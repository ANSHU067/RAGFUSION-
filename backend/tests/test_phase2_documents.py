"""Document limits and SQL/Chroma lifecycle regressions, without model downloads."""

import io
import zipfile
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
import httpx
from fastapi import HTTPException
from langchain_core.embeddings import Embeddings
from sqlalchemy import event, func, select

from app.api import documents as routes
from app.core.ingestion_limits import MAX_DOCUMENT_BYTES, MAX_DOCUMENT_CHUNKS
from app.middleware.upload_limit import UploadLimitMiddleware
from app.models.entities import Document, Embedding, SourceStatus
from app.rag.retrievers.retriever_manager import RetrieverManager
from app.schemas.document import ChunkingConfig, DocumentChunk, DocumentFormat, EmbeddingConfig, ProcessingConfig
from app.services import document as service
from test_batch2_integrity import database, owner, storage
from main import app


class TestEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return [[float(len(text)), 1.0, 0.0] for text in texts]

    def embed_query(self, text):
        return self.embed_documents([text])[0]


@pytest.fixture
def vector_store(storage, tmp_path, monkeypatch):
    manager = RetrieverManager(
        persist_directory=str(tmp_path / "chroma"),
        embedding_manager=SimpleNamespace(embeddings=TestEmbeddings()),
    )
    monkeypatch.setattr(service, "RetrieverManager", lambda: manager)
    return manager


async def stored_document(owner, text="original"):
    document = await service.upload_document(b"safe content", "test.txt", "text/plain", owner.id)
    chunks = [DocumentChunk(index=0, content=text), DocumentChunk(index=1, content="tail")]
    await service.store_document(document, chunks, [[0.1], [0.2]], EmbeddingConfig())
    return document


def vectors(manager, document):
    return manager.get_document_vectors(str(document.id), str(document.user_id))


async def test_reprocessing_purges_old_tail_and_preserves_other_documents(database, owner, vector_store):
    first, other = await stored_document(owner), await stored_document(owner, "other")
    # Legacy IDs must be found by metadata rather than an assumed ID scheme.
    vector_store.add_document_chunks({
        "ids": ["legacy-extra-chunk"], "documents": ["stale legacy text"],
        "metadatas": [{"document_id": str(first.id), "user_id": str(owner.id)}],
    })
    chunks = [DocumentChunk(index=0, content="replacement")]
    for _ in range(2):
        await service.store_document(first, chunks, [[0.3]], EmbeddingConfig())
    assert vectors(vector_store, first)["documents"] == ["replacement"]
    assert len(vectors(vector_store, other)["ids"]) == 2
    async with database.factory() as session:
        assert list(await session.scalars(select(Embedding.content).where(Embedding.document_id == first.id))) == ["replacement"]


async def test_delete_removes_vectors_sql_and_file_only_for_owner(database, owner, vector_store, storage):
    first, other = await stored_document(owner), await stored_document(owner, "other")
    # Even a forged vector sharing the document ID but another owner is outside
    # the destructive filter.
    other_owner = str(uuid4())
    vector_store.add_document_chunks({
        "ids": ["other-tenant"], "documents": ["other tenant"],
        "metadatas": [{"document_id": str(first.id), "user_id": other_owner}],
    })
    async with database.factory() as session:
        with pytest.raises(HTTPException) as denied:
            await routes.delete_document(first.id, SimpleNamespace(id=uuid4()), session)
        assert denied.value.status_code == 404
        assert len(vectors(vector_store, first)["ids"]) == 2
        response = await routes.delete_document(first.id, owner, session)
        assert response.id == first.id
    assert not vectors(vector_store, first)["ids"]
    assert len(vectors(vector_store, other)["ids"]) == 2
    assert vector_store.get_document_vectors(str(first.id), other_owner)["ids"] == ["other-tenant"]
    assert not service.resolve_storage_key(storage, first.storage_key).exists()
    async with database.factory() as session:
        assert await session.get(Document, first.id) is None
        assert await session.scalar(select(func.count()).select_from(Embedding).where(Embedding.document_id == first.id)) == 0


@pytest.mark.parametrize("operation", ["delete", "reprocess"])
async def test_vector_failures_restore_snapshot_and_sql(database, owner, vector_store, storage, monkeypatch, operation):
    document = await stored_document(owner)
    original = vectors(vector_store, document)
    if operation == "delete":
        original_delete = vector_store.delete_document_vectors
        calls = 0

        def fail_after_delete(*args):
            nonlocal calls
            original_delete(*args)
            calls += 1
            if calls == 1:
                raise RuntimeError("Injected failure after vector delete")

        monkeypatch.setattr(vector_store, "delete_document_vectors", fail_after_delete)
        async with database.factory() as session:
            with pytest.raises(HTTPException) as failed:
                await routes.delete_document(document.id, owner, session)
            assert failed.value.status_code == 503
    else:
        original_add = vector_store.add_document_chunks

        def fail_after_write(records):
            original_add(records)
            raise RuntimeError("Injected failure after vector write")

        monkeypatch.setattr(vector_store, "add_document_chunks", fail_after_write)
        with pytest.raises(service.DocumentProcessingError):
            await service.store_document(document, [DocumentChunk(index=0, content="new")], [[0.9]], EmbeddingConfig())
    assert vectors(vector_store, document)["documents"] == original["documents"]
    assert vectors(vector_store, document)["embeddings"].tolist() == original["embeddings"].tolist()
    assert service.resolve_storage_key(storage, document.storage_key).exists()
    async with database.factory() as session:
        assert await session.get(Document, document.id) is not None
        assert set(await session.scalars(select(Embedding.content).where(Embedding.document_id == document.id))) == {"original", "tail"}


@pytest.mark.parametrize("operation", ["delete", "reprocess"])
async def test_sql_commit_failure_restores_vectors(database, owner, vector_store, storage, operation):
    document = await stored_document(owner)

    def fail_commit(connection):
        raise RuntimeError("Injected SQL commit failure")

    event.listen(database.engine.sync_engine, "commit", fail_commit)
    try:
        if operation == "delete":
            async with database.factory() as session:
                with pytest.raises(HTTPException):
                    await routes.delete_document(document.id, owner, session)
        else:
            with pytest.raises(service.DocumentProcessingError):
                await service.store_document(document, [DocumentChunk(index=0, content="new")], [[0.9]], EmbeddingConfig())
    finally:
        event.remove(database.engine.sync_engine, "commit", fail_commit)
    assert set(vectors(vector_store, document)["documents"]) == {"original", "tail"}
    assert service.resolve_storage_key(storage, document.storage_key).exists()
    async with database.factory() as session:
        assert await session.get(Document, document.id) is not None
        assert set(await session.scalars(select(Embedding.content).where(Embedding.document_id == document.id))) == {"original", "tail"}


@pytest.mark.parametrize("header", [None, b"1", b"999999"])
async def test_body_limit_rejects_before_parser_even_without_honest_length(header):
    downstream = AsyncMock()
    middleware = UploadLimitMiddleware(downstream, upload_path="/documents/upload", max_file_bytes=10)
    receive = AsyncMock(side_effect=[
        {"type": "http.request", "body": b"x" * 32000, "more_body": True},
        {"type": "http.request", "body": b"x" * 34000, "more_body": True},
    ])
    send = AsyncMock()
    scope = {"type": "http", "method": "POST", "path": "/documents/upload",
             "headers": [] if header is None else [(b"content-length", header)]}
    await middleware(scope, receive, send)
    downstream.assert_not_called()
    assert send.call_args_list[0].args[0]["status"] == 413
    assert receive.await_count == (0 if header == b"999999" else 2)


async def test_body_limit_replays_valid_body_in_order():
    observed = bytearray()

    async def downstream(scope, receive, send):
        while True:
            message = await receive()
            observed.extend(message["body"])
            if not message["more_body"]:
                break

    middleware = UploadLimitMiddleware(downstream, upload_path="/upload", max_file_bytes=100000)
    body = b"x" * 70000 + b"y" * 100
    receive = AsyncMock(side_effect=[{"type": "http.request", "body": body, "more_body": False}])
    await middleware({"type": "http", "method": "POST", "path": "/upload", "headers": []}, receive, AsyncMock())
    assert observed == body


async def test_file_limit_counts_bytes_when_upload_size_is_missing(monkeypatch):
    limit = 1024 * 1024
    source = io.BytesIO(b"x" * (limit + 1))
    sizes = []

    async def read(size):
        sizes.append(size)
        return source.read(size)

    monkeypatch.setattr(routes, "get_settings", lambda: SimpleNamespace(max_file_size_mb=1))
    upload = AsyncMock()
    monkeypatch.setattr(routes, "upload_document", upload)
    file = SimpleNamespace(size=None, read=read)
    with pytest.raises(HTTPException) as failed:
        await routes.upload_document_route(file, SimpleNamespace(id=uuid4()), AsyncMock())
    assert failed.value.status_code == 413
    assert all(0 < size <= 65536 for size in sizes)
    upload.assert_not_called()


async def test_service_rejects_oversize_before_writing(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "get_settings", lambda: SimpleNamespace(upload_dir=str(tmp_path), max_file_size_mb=100))
    with pytest.raises(service.DocumentValidationError) as failed:
        await service.upload_document(b"x" * (MAX_DOCUMENT_BYTES + 1), "big.txt", "text/plain", uuid4())
    assert failed.value.code == "FILE_TOO_LARGE"
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("content", [b"\x7fELFhello", b"MZexecutable", b"hello\x00binary", b"\xff\xfeinvalid", b"a" * 65536 + b"\x00"])
@pytest.mark.parametrize("mime", ["text/plain", "text/csv", "text/markdown"])
def test_binary_disguised_as_text_is_rejected(tmp_path, content, mime):
    path = tmp_path / "disguised.txt"
    path.write_bytes(content)
    with pytest.raises(service.DocumentValidationError):
        service.validate_file(path, mime, len(content))


def test_valid_utf8_text_can_cross_read_boundary(tmp_path):
    content = ("a" * 65535 + "é\n世界").encode()
    path = tmp_path / "valid.txt"
    path.write_bytes(content)
    assert service.validate_file(path, "text/plain", len(content)) == DocumentFormat.txt


def test_docx_expansion_is_rejected_before_document_parser(tmp_path, monkeypatch):
    path = tmp_path / "bomb.docx"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", "x")
        archive.writestr("word/document.xml", "x" * 1000)
    monkeypatch.setattr(service, "MAX_DOCX_EXPANDED_BYTES", 100)
    parser = Mock(side_effect=AssertionError("Parser must not run"))
    monkeypatch.setattr(service, "DocxDocument", parser)
    with pytest.raises(service.DocumentValidationError) as failed:
        service.validate_file(path, None, path.stat().st_size)
    assert failed.value.code == "EXTRACTION_LIMIT"
    parser.assert_not_called()


def test_fixed_chunks_accept_exact_limit_and_reject_one_more():
    config = ChunkingConfig(strategy="fixed", chunk_size=100, chunk_overlap=0)
    assert len(service.chunk_text("word " * (75 * MAX_DOCUMENT_CHUNKS), config)) == MAX_DOCUMENT_CHUNKS
    with pytest.raises(service.DocumentValidationError) as failed:
        service.chunk_text("word " * (75 * MAX_DOCUMENT_CHUNKS + 1), config)
    assert failed.value.code == "TOO_MANY_CHUNKS"


@pytest.mark.parametrize("strategy,module,function", [
    ("semantic", "unstructured.chunking.title", "chunk_by_title"),
    ("recursive", "unstructured.chunking.basic", "chunk_elements"),
])
def test_unstructured_chunk_limits(monkeypatch, strategy, module, function):
    monkeypatch.setattr(service, "partition_text", lambda **kwargs: [])
    monkeypatch.setattr(f"{module}.{function}", lambda *args, **kwargs: ["chunk"] * (MAX_DOCUMENT_CHUNKS + 1))
    with pytest.raises(service.DocumentValidationError) as failed:
        service.chunk_text("text", ChunkingConfig(strategy=strategy))
    assert failed.value.code == "TOO_MANY_CHUNKS"


async def test_processing_rejects_excess_chunks_before_embedding(database, owner, storage, monkeypatch):
    document = await service.upload_document(b"safe content", "test.txt", "text/plain", owner.id)
    chunks = [DocumentChunk(index=0, content="chunk")] * (MAX_DOCUMENT_CHUNKS + 1)
    monkeypatch.setattr(service, "chunk_text", lambda *args: chunks)
    embed = AsyncMock()
    monkeypatch.setattr(service, "generate_embeddings", embed)
    with pytest.raises(service.DocumentValidationError) as failed:
        await service.process_document(document.id, None, DocumentFormat.txt, ProcessingConfig(clean_text=False))
    assert failed.value.code == "TOO_MANY_CHUNKS"
    embed.assert_not_called()
    async with database.factory() as session:
        assert (await session.get(Document, document.id)).status == SourceStatus.failed


@pytest.fixture
def document_api(database, owner):
    async def current_user():
        return owner

    async def session():
        async with database.factory() as db:
            yield db

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[routes.get_current_user] = current_user
    app.dependency_overrides[routes.get_db_session] = session
    try:
        yield app
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


async def test_upload_reprocess_delete_http_lifecycle(document_api, vector_store, monkeypatch, database, storage):
    async def embed(chunks, *args):
        return [[0.1] for _ in chunks]

    monkeypatch.setattr(service, "generate_embeddings", embed)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=document_api), base_url="http://test") as client:
        response = await client.post(
            "/api/v1/documents/upload?chunking_strategy=fixed&clean_text=false",
            files={"file": ("test.txt", b"word " * 2000, "text/plain")},
        )
        assert response.status_code == 202, response.text
        assert response.json()["status"] == "ready"
        document_id = response.json()["document_id"]
        response = await client.post(
            f"/api/v1/documents/{document_id}/reprocess?chunking_strategy=fixed&chunk_size=10000&clean_text=false",
        )
        assert response.status_code == 200, response.text
        collection = vector_store.client.get_collection(vector_store.collection_name)
        assert len(collection.get(where={"document_id": document_id})["ids"]) == 1
        response = await client.delete(f"/api/v1/documents/{document_id}")
        assert response.status_code == 200, response.text
        assert not collection.get(where={"document_id": document_id})["ids"]
    assert not list(storage.rglob("content"))
    async with database.factory() as session:
        assert await session.scalar(select(func.count()).select_from(Document)) == 0


async def test_http_rejects_disguised_binary_without_sql_or_file(document_api, storage, database):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=document_api), base_url="http://test") as client:
        response = await client.post("/api/v1/documents/upload", files={"file": ("safe.txt", b"\x7fELFpayload", "text/plain")})
    assert response.status_code == 400, response.text
    assert not list(storage.rglob("content"))
    async with database.factory() as session:
        assert await session.scalar(select(func.count()).select_from(Document)) == 0


async def test_http_chunk_limit_is_413_and_never_embeds(document_api, storage, database, monkeypatch):
    monkeypatch.setattr(service, "chunk_text", lambda *args: [DocumentChunk(index=0, content="chunk")] * (MAX_DOCUMENT_CHUNKS + 1))
    embed = AsyncMock()
    monkeypatch.setattr(service, "generate_embeddings", embed)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=document_api), base_url="http://test") as client:
        response = await client.post("/api/v1/documents/upload?clean_text=false", files={"file": ("test.txt", b"safe content", "text/plain")})
        assert response.status_code == 413, response.text
        async with database.factory() as session:
            document = await session.scalar(select(Document))
            document_id = document.id
        response = await client.post(f"/api/v1/documents/{document_id}/reprocess?clean_text=false")
        assert response.status_code == 413, response.text
    embed.assert_not_called()


def test_valid_docx_signature_and_structure_are_accepted(tmp_path):
    from docx import Document as DocxDocument

    document = DocxDocument()
    document.add_paragraph("Valid document content")
    path = tmp_path / "valid.docx"
    document.save(path)
    assert service.validate_file(path, None, path.stat().st_size) == DocumentFormat.docx

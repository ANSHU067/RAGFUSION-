"""Ingestion budgets cannot occupy the event loop or API dependency workers."""

import asyncio
import threading
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import anyio
import httpx
import numpy as np
import pytest

from app.core.worker_limits import INGEST_LIMITER, VECTOR_LIMITER
from app.schemas.document import DocumentFormat, ProcessingConfig
from app.services import document, embedding_helper
from main import app


@pytest.mark.asyncio
async def test_list_endpoints_respond_while_all_parsers_are_busy(test_db, auth_headers, monkeypatch):
    loop_thread = threading.get_ident()
    started = [threading.Event(), threading.Event()]
    release = threading.Event()
    threads = []
    paths = ["first", "second"]

    def parse(path, _format):
        threads.append(threading.get_ident())
        started[paths.index(path)].set()
        if not release.wait(timeout=10):
            raise TimeoutError("Test worker was not released")

    monkeypatch.setattr(document, "extract_text", parse)
    tasks = [asyncio.create_task(anyio.to_thread.run_sync(
        document.extract_text, path, DocumentFormat.txt, limiter=INGEST_LIMITER,
    )) for path in paths]
    try:
        async with asyncio.timeout(3):
            while not all(event.is_set() for event in started):
                await asyncio.sleep(0.01)
        assert INGEST_LIMITER.borrowed_tokens == 2
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            async with asyncio.timeout(3):
                responses = await asyncio.gather(
                    client.get("/api/v1/documents", headers=auth_headers),
                    client.get("/api/v1/youtube", headers=auth_headers),
                    anyio.to_thread.run_sync(lambda: "vector operations available", limiter=VECTOR_LIMITER),
                )
        assert [response.status_code for response in responses[:2]] == [200, 200]
        assert responses[2] == "vector operations available"
        assert all(thread != loop_thread for thread in threads)
    finally:
        release.set()
        await asyncio.gather(*tasks)


@pytest.mark.asyncio
async def test_document_processing_offloads_each_sync_stage(monkeypatch):
    loop_thread = threading.get_ident()
    workers = []
    owner = SimpleNamespace(storage_key="uploads/test/content", mime_type="text/plain", size_bytes=4,
                            filename="test.txt", status=None)
    session = AsyncMock()
    session.get.return_value = owner
    context = AsyncMock()
    context.__aenter__.return_value = session
    monkeypatch.setattr(document, "get_session_factory", lambda: lambda: context)
    monkeypatch.setattr(document, "get_settings", lambda: SimpleNamespace(upload_dir="/tmp"))

    def stage(value):
        def run(*args):
            workers.append(threading.get_ident())
            return value
        return run

    metadata = Mock()
    metadata.model_dump.return_value = {}
    monkeypatch.setattr(document, "validate_file", stage(DocumentFormat.txt))
    monkeypatch.setattr(document, "extract_text", stage(("text", metadata)))
    monkeypatch.setattr(document, "clean_text", stage("text"))
    monkeypatch.setattr(document, "chunk_text", stage([]))
    monkeypatch.setattr(document, "generate_embeddings", AsyncMock(return_value=[]))
    monkeypatch.setattr(document, "store_document", AsyncMock())
    from uuid import uuid4
    await document.process_document(uuid4(), None, DocumentFormat.txt, ProcessingConfig())
    assert len(workers) == 4
    assert all(worker != loop_thread for worker in workers)


@pytest.mark.asyncio
async def test_embedding_result_conversion_does_not_block_event_loop(monkeypatch):
    loop_thread = threading.get_ident()
    class Result:
        def tolist(self):
            assert threading.get_ident() != loop_thread
            return np.ones((1, 384)).tolist()
    service = SimpleNamespace(get_provider=Mock(), embed_texts=AsyncMock(return_value=Result()))
    monkeypatch.setattr(embedding_helper, "get_embedding_service", lambda: service)
    assert len((await embedding_helper.generate_embeddings(["text"], "all-minilm-l6-v2"))[0]) == 384


@pytest.mark.asyncio
async def test_pipeline_initialization_recovers_after_backoff(monkeypatch):
    from app.api import chat
    state = SimpleNamespace(rag_pipeline=None, rag_pipeline_lock=asyncio.Lock())
    request = SimpleNamespace(app=SimpleNamespace(state=state))
    user = SimpleNamespace(id="owner")
    pipeline = object()
    factory = Mock(side_effect=[ValueError("temporary Chroma failure"), pipeline])
    monkeypatch.setattr(chat, "RAGPipeline", factory)
    monkeypatch.setattr(chat, "SettingsRepository", lambda db: SimpleNamespace(get_by_user_id=AsyncMock(return_value=None)))
    monkeypatch.setattr(chat, "ChatService", lambda **kwargs: kwargs)
    await chat.get_chat_service(request, None, user)
    await chat.get_chat_service(request, None, user)
    assert factory.call_count == 1
    state.rag_pipeline_retry_after = 0
    result = await chat.get_chat_service(request, None, user)
    assert result["rag_pipeline"] is pipeline
    assert result["pipeline_error"] is None

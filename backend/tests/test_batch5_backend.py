"""Behavioral checks for sanitized errors, bounded history and shared resources."""

import asyncio
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, field_validator
from sqlalchemy import event, func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.exceptions import AppException, NotFoundError, ValidationError, register_exception_handlers
from app.models.entities import ChatSession, Message, MessageRole
from app.schemas.history import HistoryFilterParams, HistoryPaginationParams, HistorySearchRequest, HistorySortParams
from app.services.chat_service import ChatService
from app.services.history_service import HistoryService
from app.services.memory_service import MemoryService

SECRET = "private-path-/var/lib/docpro/secret.db UNIQUE users_private_idx vendor-token"


class ErrorInput(BaseModel):
    count: int

    @field_validator("count")
    @classmethod
    def validate_count(cls, value):
        if value < 0:
            raise ValueError(SECRET)
        return value


@pytest.mark.parametrize("kind,expected", [
    ("request", 422), ("pydantic", 422), ("application", 422),
    ("integrity", 409), ("database", 500), ("unknown", 500),
])
def test_uniform_sanitized_errors(kind, expected):
    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/input")
    async def input_route(data: ErrorInput):
        return data

    @app.get("/error")
    async def error_route():
        if kind == "pydantic":
            ErrorInput(count=-1)
        if kind == "application":
            raise ValidationError("Invalid configuration")
        if kind == "integrity":
            raise IntegrityError("insert private_table", {}, Exception(SECRET))
        if kind == "database":
            raise SQLAlchemyError(SECRET)
        raise RuntimeError(SECRET)

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/input", json={"count": -1}) if kind == "request" else client.get("/error")
    assert response.status_code == expected
    assert SECRET not in response.text
    assert "private_table" not in response.text
    if kind in {"request", "pydantic"}:
        error = response.json()["error"]
        assert error["type"] == "ValidationError"
        assert error["message"] == "Data validation failed"
        assert error["details"]["errors"] == [
            {"field": "body.count" if kind == "request" else "count", "message": "Invalid value", "type": "value_error"}
        ]


def test_debug_never_enables_tracebacks(monkeypatch):
    from app.config.settings import get_settings
    from main import create_app
    monkeypatch.setattr(get_settings(), "debug", True)
    app = create_app()

    @app.get("/debug-error")
    async def error():
        raise RuntimeError(SECRET)

    response = TestClient(app, raise_server_exceptions=False).get("/debug-error")
    assert response.status_code == 500
    assert SECRET not in response.text
    assert "Traceback" not in response.text


@pytest.mark.asyncio
async def test_history_counts_sort_before_pagination_without_n_plus_one(db_session, test_user):
    sessions = []
    for index, count in enumerate([0, 4, 1, 2]):
        session = ChatSession(user_id=test_user.id, title=f"Session {index}", updated_at=datetime(2020, 1, 1) + timedelta(days=index))
        db_session.add(session)
        await db_session.flush()
        db_session.add_all([Message(chat_session_id=session.id, role=MessageRole.user, content="hello") for _ in range(count)])
        sessions.append(session)
    await db_session.commit()
    statements = []
    engine = db_session.bind.sync_engine

    def capture(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", capture)
    try:
        service = HistoryService(db_session)
        response = await service.list_sessions(
            test_user.id, HistoryPaginationParams(page_size=2),
            HistorySortParams(sort_by="message_count", sort_order="desc"), HistoryFilterParams(),
        )
        assert [s.message_count for s in response.sessions] == [4, 2]
        assert response.total == 4
        assert len(statements) == 2
        statements.clear()
        found = await service.search_sessions(test_user.id, HistorySearchRequest(query="Session"))
        assert sorted(s.message_count for s in found) == [0, 1, 2, 4]
        assert len(statements) == 1
    finally:
        event.remove(engine, "before_cursor_execute", capture)


@pytest.mark.asyncio
async def test_trash_blocks_reads_updates_and_new_messages(db_session, test_user):
    memory = MemoryService(db_session)
    session = await memory.create_session(test_user.id)
    await memory.add_message(session.id, MessageRole.user, "before trash")
    await HistoryService(db_session).delete_session(session.id, test_user.id)
    assert await memory.get_session(session.id, test_user.id) is None
    assert await memory.list_sessions(test_user.id) == ([], 0)
    assert await memory.get_messages(session.id) == []
    assert await memory.get_context_messages(session.id) == []
    assert await memory.update_session_title(session.id, test_user.id, "wrong") is None
    with pytest.raises(NotFoundError):
        await memory.add_message(session.id, MessageRole.user, "after trash")
    assert await db_session.scalar(select(func.count()).select_from(Message)) == 1


@pytest.mark.asyncio
async def test_message_reads_bounded_and_session_lookup_does_not_load_messages(db_session, test_user):
    memory = MemoryService(db_session)
    session = await memory.create_session(test_user.id)
    db_session.add_all([Message(chat_session_id=session.id, role=MessageRole.user, content=str(i)) for i in range(151)])
    await db_session.commit()
    assert len(await memory.get_messages(session.id)) == 100
    assert len(await memory.get_messages(session.id, limit=500, offset=100)) == 51
    from sqlalchemy import inspect
    lookup = await memory.get_session(session.id, test_user.id)
    assert "messages" in inspect(lookup).unloaded
    renamed = await memory.update_session_title(session.id, test_user.id, "renamed")
    assert "messages" in inspect(renamed).unloaded


@pytest.mark.asyncio
async def test_chat_and_sse_errors_are_not_persisted(db_session, test_user, monkeypatch):
    service = ChatService(db_session, test_user.id, rag_pipeline=MagicMock())
    monkeypatch.setattr(service, "_run_rag_pipeline", AsyncMock(side_effect=RuntimeError(SECRET)))
    with pytest.raises(AppException) as error:
        await service.chat("hello")
    assert error.value.status_code == 502
    assert error.value.message == "Chat generation failed"
    chunks = [chunk async for chunk in service.chat_stream("hello")]
    assert chunks[-1].error == "Chat generation failed"
    messages = (await db_session.scalars(select(Message))).all()
    assert all(message.role == MessageRole.user for message in messages)
    assert all(SECRET not in message.content for message in messages)


@pytest.mark.asyncio
async def test_transcript_deadline_includes_fallback_and_keeps_loop_responsive(monkeypatch):
    from app.services import youtube_service as youtube
    started = threading.Event()
    finished = threading.Event()

    def blocked(*args):
        started.set()
        finished.wait(1)
        return "late transcript"

    monkeypatch.setattr(youtube, "YouTubeTranscriptApi", object())
    monkeypatch.setattr(youtube, "_fetch_transcript_sync", blocked)
    monkeypatch.setattr(youtube, "TRANSCRIPT_TIMEOUT", 0.05)
    before = time.monotonic()
    try:
        task = asyncio.create_task(youtube.fetch_transcript("dQw4w9WgXcQ"))
        await asyncio.sleep(0.01)
        assert started.is_set()
        with pytest.raises(youtube.YouTubeIngestionError) as error:
            await task
        assert error.value.code == "TRANSCRIPT_TIMEOUT"
        assert time.monotonic() - before < 0.5
    finally:
        finished.set()


def test_transcript_socket_deadlines_and_disabled_transcripts_do_not_retry(monkeypatch):
    from app.services import youtube_service as youtube
    captured = []
    monkeypatch.setattr(youtube.HTTPSession, "send", lambda self, request, **kwargs: captured.append(kwargs))
    with youtube.TranscriptSession(time.monotonic() + 10) as session:
        session.send(object(), timeout=None)
    assert captured[0]["timeout"] == (3.0, 5.0)
    calls = []

    class NoTranscriptFound(Exception):
        pass

    class API:
        def __init__(self, **kwargs):
            pass

        def fetch(self, *args, **kwargs):
            calls.append("fetch")
            raise RuntimeError(SECRET)

        def list(self, *args):
            calls.append("list")

    monkeypatch.setitem(sys.modules, "youtube_transcript_api", SimpleNamespace(NoTranscriptFound=NoTranscriptFound))
    monkeypatch.setattr(youtube, "YouTubeTranscriptApi", API)
    with pytest.raises(RuntimeError):
        youtube._fetch_transcript_sync("video", ["en"], time.monotonic() + 20)
    assert calls == ["fetch"]


@pytest.mark.asyncio
async def test_encoder_shared_by_concurrent_retrieval_and_ingestion(monkeypatch):
    from app.core import embedding_runtime as runtime
    from app.rag.embeddings.embedding_manager import EmbeddingManager
    from app.config.embedding_config import get_embedding_config
    from app.services.embedding_service import SentenceTransformerProvider
    from app.config.settings import get_settings
    calls = []

    class Encoder:
        def __init__(self, *args, **kwargs):
            time.sleep(0.01)
            calls.append(kwargs)

        def encode(self, texts, **kwargs):
            return np.ones((len(texts), 384))

    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=Encoder))
    monkeypatch.setattr(get_settings(), "embedding_local_files_only", True)
    runtime._load_model.cache_clear()
    try:
        with ThreadPoolExecutor(max_workers=6) as executor:
            models = list(executor.map(lambda _: runtime.get_sentence_transformer(), range(12)))
        assert all(model is models[0] for model in models)
        manager = EmbeddingManager()
        assert len(manager.embed_query("query")) == 384
        provider = SentenceTransformerProvider(get_embedding_config("all-minilm-l6-v2"))
        assert (await provider.embed_texts(["document"])).shape == (1, 384)
        assert provider._model is models[0]
        assert len(calls) == 1
        assert calls[0]["local_files_only"] is True
    finally:
        runtime._load_model.cache_clear()


def test_chroma_telemetry_never_calls_posthog(monkeypatch, tmp_path):
    import posthog
    import chromadb
    from chromadb.config import Settings
    capture = MagicMock(side_effect=AssertionError("PostHog must not be called"))
    monkeypatch.setattr(posthog, "capture", capture)
    client = chromadb.PersistentClient(path=str(tmp_path / "chroma"), settings=Settings(
        anonymized_telemetry=False,
        chroma_product_telemetry_impl="app.core.telemetry.DisabledProductTelemetry",
        chroma_telemetry_impl="app.core.telemetry.DisabledProductTelemetry",
    ))
    collection = client.get_or_create_collection("batch5-test")
    collection.add(ids=["a"], documents=["text"], embeddings=[[1.0, 0.0]])
    assert collection.count() == 1
    capture.assert_not_called()


def test_trashed_session_returns_404_in_normal_chat_routes(client, auth_headers, monkeypatch):
    from main import app
    monkeypatch.setattr(app.state, "rag_pipeline", MagicMock())
    response = client.post("/api/v1/chat/sessions", json={"title": "Trash"}, headers=auth_headers)
    session_id = response.json()["id"]
    assert client.delete(f"/api/v1/history/{session_id}", headers=auth_headers).status_code == 200
    assert client.get(f"/api/v1/chat/sessions/{session_id}", headers=auth_headers).status_code == 404
    for endpoint in ("/api/v1/chat", "/api/v1/chat/stream"):
        result = client.post(endpoint, headers=auth_headers, json={"message": "hello", "session_id": session_id})
        assert result.status_code == 404
    result = client.get("/api/v1/chat/sessions", headers=auth_headers)
    assert all(item["id"] != session_id for item in result.json()["sessions"])


@pytest.mark.parametrize("code,status", [("TRANSCRIPT_TIMEOUT", 504), ("TRANSCRIPT_FETCH_FAILED", 400)])
def test_youtube_errors_have_safe_status_and_message(client, auth_headers, monkeypatch, code, status):
    from app.api import youtube
    monkeypatch.setattr(youtube, "ingest_youtube", AsyncMock(side_effect=youtube.YouTubeIngestionError(SECRET, code=code)))
    response = client.post("/api/v1/youtube/ingest", headers=auth_headers, json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"})
    assert response.status_code == status
    assert SECRET not in response.text


def test_chunk_validation_uses_uniform_handler_before_upload(client, auth_headers, monkeypatch):
    from app.api import documents
    upload = AsyncMock()
    monkeypatch.setattr(documents, "upload_document", upload)
    response = client.post(
        "/api/v1/documents/upload?chunk_size=100&chunk_overlap=100", headers=auth_headers,
        files={"file": ("example.txt", b"example", "text/plain")},
    )
    assert response.status_code == 422
    assert response.json()["error"]["message"] == "Data validation failed"
    upload.assert_not_called()

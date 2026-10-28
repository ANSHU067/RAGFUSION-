"""Real local Chroma schema recovery without downloading an embedding model."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from threading import Barrier
from types import SimpleNamespace

import pytest
from langchain_core.embeddings import Embeddings

from app.core import chroma_runtime
from app.rag.retrievers.retriever_manager import RetrieverManager


class Encoder(Embeddings):
    def embed_documents(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]

    def embed_query(self, text):
        return self.embed_documents([text])[0]


def retriever(path):
    return RetrieverManager(
        persist_directory=str(path), embedding_manager=SimpleNamespace(embeddings=Encoder()),
    )


def test_concurrent_first_clients_initialize_missing_directory(tmp_path):
    path = tmp_path / "new" / "vectors"
    barrier = Barrier(8)

    def connect(_):
        barrier.wait(timeout=5)
        return chroma_runtime.get_chroma_client(str(path))

    with ThreadPoolExecutor(max_workers=8) as workers:
        clients = list(workers.map(connect, range(8)))
    assert path.is_dir()
    assert all(client.tenant == "default_tenant" for client in clients)
    assert all(client._system is clients[0]._system for client in clients)


@pytest.mark.parametrize("damage", ["DROP TABLE tenants", "DELETE FROM tenants"])
def test_missing_tenant_schema_or_record_recovers_without_losing_vectors(tmp_path, damage):
    path = tmp_path / "vectors"
    original = retriever(path)
    original.add_document_chunks({
        "ids": ["mine", "theirs"], "documents": ["my text", "their text"],
        "embeddings": [[1., 0., 0.], [0., 1., 0.]],
        "metadatas": [{"document_id": "doc", "user_id": owner} for owner in ("me", "other")],
    })
    with closing(sqlite3.connect(path / "chroma.sqlite3")) as db, db:
        db.execute(damage)
    recovered = retriever(path)
    assert recovered.get_collection_stats()["count"] == 2
    recovered.delete_document_vectors("doc", "me")
    assert recovered.get_document_vectors("doc", "me")["ids"] == []
    assert recovered.get_document_vectors("doc", "other")["documents"] == ["their text"]


def test_missing_default_database_can_be_initialized(tmp_path):
    path = tmp_path / "vectors"
    chroma_runtime.get_chroma_client(str(path))
    with closing(sqlite3.connect(path / "chroma.sqlite3")) as db, db:
        db.execute("DELETE FROM databases WHERE name='default_database'")
    assert retriever(path).get_collection_stats()["count"] == 0


def test_corrupt_database_is_not_erased_or_replaced(tmp_path):
    path = tmp_path / "chroma.sqlite3"
    path.write_bytes(b"damaged database that must remain available for recovery")
    original = path.read_bytes()
    with pytest.raises(Exception):
        retriever(tmp_path)
    assert path.read_bytes() == original


def test_lost_database_record_does_not_hide_existing_collections(tmp_path):
    store = retriever(tmp_path)
    store.add_document_chunks({
        "ids": ["chunk"], "documents": ["text"], "embeddings": [[1., 0., 0.]],
        "metadatas": [{"document_id": "doc", "user_id": "owner"}],
    })
    with closing(sqlite3.connect(tmp_path / "chroma.sqlite3")) as db, db:
        original = db.execute("SELECT id, database_id FROM collections").fetchall()
        db.execute("DELETE FROM databases WHERE name='default_database'")
    with pytest.raises(RuntimeError, match="ownership requires operator recovery"):
        retriever(tmp_path)
    with closing(sqlite3.connect(tmp_path / "chroma.sqlite3")) as db:
        assert db.execute("SELECT id, database_id FROM collections").fetchall() == original
        assert db.execute("SELECT COUNT(*) FROM databases").fetchone()[0] == 0


def test_recovery_retries_once(monkeypatch, tmp_path):
    import chromadb
    from unittest.mock import Mock

    connect = Mock(side_effect=ValueError("Could not connect to tenant default_tenant"))
    repair = Mock()
    monkeypatch.setattr(chromadb, "PersistentClient", connect)
    monkeypatch.setattr(chroma_runtime, "_recover_defaults", repair)
    with pytest.raises(ValueError):
        chroma_runtime.get_chroma_client(str(tmp_path))
    assert connect.call_count == 2
    repair.assert_called_once()


def test_precomputed_vectors_are_stored_without_embedding_again(tmp_path, monkeypatch):
    store = retriever(tmp_path)
    def forbidden(*args, **kwargs):
        raise AssertionError("Already embedded chunks must not invoke the model again")
    monkeypatch.setattr(store.embedding_manager.embeddings, "embed_documents", forbidden)
    store.add_document_chunks({
        "ids": ["chunk"], "documents": ["text"], "embeddings": [[0., 0., 1.]],
        "metadatas": [{"document_id": "doc", "user_id": "owner"}],
    })
    assert store.get_document_vectors("doc", "owner")["embeddings"].tolist() == [[0., 0., 1.]]

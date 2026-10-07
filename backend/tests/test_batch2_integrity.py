"""Batch 2 regressions against migrated SQLite and optional isolated PostgreSQL.

Set BATCH2_POSTGRES_URL to a test server where the role can create databases.
Every PostgreSQL test creates/drops its own randomly named database.
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from sqlalchemy import event, func, inspect, select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api import documents as routes
from app.config.settings import Settings
from app.db.session import to_async_database_url
from app.models.entities import Document, Embedding, User, Website
from app.models.settings import UserSettings
from app.repositories.settings_repository import SettingsRepository
from app.schemas.document import DocumentChunk, DocumentFormat, EmbeddingConfig, ProcessingConfig
from app.schemas.settings import SettingsUpdate
from app.services import document as service
from app.services.settings_service import SettingsService, SettingsValidationError

ROOT = Path(__file__).resolve().parents[2]
PREVIOUS = "7efa7e63b3ce"


def migration_config(url):
    config = Config(str(ROOT / "backend/alembic.ini"))
    config.set_main_option("sqlalchemy.url", str(url).replace("%", "%%"))
    return config


@pytest_asyncio.fixture(params=["sqlite", "postgresql"])
async def database(request, tmp_path):
    admin = None
    name = "batch2_" + uuid4().hex
    if request.param == "postgresql":
        configured = os.environ.get("BATCH2_POSTGRES_URL")
        if not configured:
            pytest.skip("Set BATCH2_POSTGRES_URL for real PostgreSQL verification")
        url = make_url(to_async_database_url(configured)).set(database=name)
        admin = create_async_engine(to_async_database_url(configured), isolation_level="AUTOCOMMIT")
        async with admin.connect() as connection:
            await connection.execute(text(f'CREATE DATABASE "{name}"'))
        migration_url = url.render_as_string(hide_password=False)
    else:
        url = f"sqlite+aiosqlite:///{tmp_path / 'integrity.sqlite'}"
        migration_url = f"sqlite:///{tmp_path / 'integrity.sqlite'}"
    engine = create_async_engine(url)
    if request.param == "sqlite":
        @event.listens_for(engine.sync_engine, "connect")
        def foreign_keys(connection, record):
            connection.execute("PRAGMA foreign_keys=ON")
    try:
        await asyncio.to_thread(command.upgrade, migration_config(migration_url), "head")
        yield SimpleNamespace(engine=engine, factory=async_sessionmaker(engine, expire_on_commit=False),
                              migration_url=migration_url, dialect=request.param)
    finally:
        await engine.dispose()
        if admin is not None:
            async with admin.connect() as connection:
                await connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
            await admin.dispose()


@pytest_asyncio.fixture
async def owner(database):
    async with database.factory() as session:
        user = User(email=f"{uuid4()}@example.invalid")
        session.add(user)
        await session.commit()
        return user


@pytest.fixture
def storage(database, tmp_path, monkeypatch):
    root = tmp_path / "uploads-root"
    settings = SimpleNamespace(upload_dir=str(root), max_file_size_mb=15)
    monkeypatch.setattr(service, "get_settings", lambda: settings)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)
    monkeypatch.setattr(service, "get_session_factory", lambda: database.factory)
    retriever = Mock()
    retriever.add_documents.side_effect = lambda **values: values["ids"]
    monkeypatch.setattr(service, "RetrieverManager", lambda: retriever)
    return root


def test_configuration_precedence_and_local_default(monkeypatch, tmp_path):
    monkeypatch.delenv("DOCPRO_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert make_url(Settings(_env_file=None).database_url).host == "localhost"
    generic = "postgresql+asyncpg://generic:secret@localhost/generic"
    prefixed = "postgresql+asyncpg://preferred:secret@localhost/preferred"
    monkeypatch.setenv("DATABASE_URL", generic)
    assert Settings(_env_file=None).database_url == generic
    monkeypatch.setenv("DOCPRO_DATABASE_URL", prefixed)
    assert Settings(_env_file=None).database_url == prefixed
    monkeypatch.delenv("DOCPRO_DATABASE_URL")
    monkeypatch.delenv("DATABASE_URL")
    dotenv_file = tmp_path / "settings.env"
    dotenv_file.write_text(f"DATABASE_URL={generic}\n")
    assert Settings(_env_file=dotenv_file).database_url == generic


@pytest.mark.parametrize("driver", ["postgresql", "postgresql+psycopg", "postgresql+asyncpg"])
def test_password_round_trip(driver):
    original = URL.create(driver, username="test", password="p@ss:/?#%+word", host="localhost", database="test")
    converted = make_url(to_async_database_url(original.render_as_string(hide_password=False)))
    assert converted.password == original.password
    assert converted.drivername == "postgresql+asyncpg"


def test_storage_helper_rejects_escapes_and_symlinks(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "link").symlink_to(outside, target_is_directory=True)
    for key in ["../outside/file", str(outside / "file"), "link/file", "", ".", "a/../../file", "a\\..\\file"]:
        with pytest.raises(service.DocumentValidationError, match="Invalid document storage location"):
            service.resolve_storage_key(root, key)
    assert service.resolve_storage_key(root, "uploads/user/doc/content") == root / "uploads/user/doc/content"


async def test_upload_filename_is_metadata_only(database, owner, storage):
    for filename in ["../../../../outside.txt", "/absolute.txt", "..\\..\\outside.txt"]:
        doc = await service.upload_document(b"safe content", filename, "text/plain", owner.id)
        assert doc.filename == filename
        assert doc.storage_key == f"uploads/{owner.id}/{doc.id}/content"
        assert service.resolve_storage_key(storage, doc.storage_key).read_bytes() == b"safe content"
    assert not (storage.parent / "outside.txt").exists()


async def test_invalid_upload_removes_uncommitted_file(database, owner, storage):
    with pytest.raises(service.DocumentValidationError):
        await service.upload_document(b"", "empty.txt", "text/plain", owner.id)
    assert not list(storage.rglob("content"))
    async with database.factory() as session:
        assert await session.scalar(select(func.count()).select_from(Document)) == 0


async def test_reprocess_and_delete_block_unsafe_keys_and_other_tenants(database, owner, storage, monkeypatch):
    outside = storage.parent / "protected.txt"
    outside.write_text("protected")
    async with database.factory() as session:
        document = Document(user_id=owner.id, filename="display.txt", storage_key="../protected.txt", mime_type="text/plain")
        session.add(document)
        await session.commit()
        for operation in (routes.delete_document, routes.reprocess_document):
            with pytest.raises(HTTPException) as denied:
                await operation(document.id, SimpleNamespace(id=uuid4()), session)
            assert denied.value.status_code == 404
            with pytest.raises(HTTPException) as invalid:
                await operation(document.id, owner, session)
            assert invalid.value.status_code == 400
        extractor = Mock(side_effect=AssertionError("Unsafe file was read"))
        monkeypatch.setattr(service, "extract_text", extractor)
        with pytest.raises(service.DocumentValidationError):
            await service.process_document(document.id, outside, DocumentFormat.txt, ProcessingConfig())
        extractor.assert_not_called()
        assert outside.read_text() == "protected"
        assert await session.get(Document, document.id) is not None


async def test_reingestion_replaces_chunks_and_preserves_other_documents(database, owner, storage):
    first = await service.upload_document(b"content", "one.txt", "text/plain", owner.id)
    second = await service.upload_document(b"content", "two.txt", "text/plain", owner.id)
    chunks = [DocumentChunk(index=0, content="old", metadata={"page": 7}), DocumentChunk(index=1, content="tail")]
    await service.store_document(first, chunks, [[.1], [.2]], EmbeddingConfig())
    await service.store_document(second, chunks, [[.1], [.2]], EmbeddingConfig())
    replacement = [DocumentChunk(index=0, content="new", metadata={"page": 9})]
    for _ in range(2):
        await service.store_document(first, replacement, [[.3]], EmbeddingConfig())
    async with database.factory() as session:
        rows = (await session.scalars(select(Embedding).where(Embedding.document_id == first.id))).all()
        assert [(row.chunk_index, row.content, row.metadata_) for row in rows] == [(0, "new", {"page": 9})]
        assert await session.scalar(select(func.count()).select_from(Embedding).where(Embedding.document_id == second.id)) == 2
        session.add(Embedding(document_id=first.id, chunk_index=0, content="duplicate", vector=[.1], model_name="test"))
        with pytest.raises(IntegrityError):
            await session.flush()


async def test_replace_rolls_back_on_database_error(database, owner, storage):
    document = await service.upload_document(b"content", "one.txt", "text/plain", owner.id)
    chunks = [DocumentChunk(index=0, content="original")]
    await service.store_document(document, chunks, [[.1]], EmbeddingConfig())

    def reject_insert(connection, cursor, statement, parameters, context, many):
        if statement.lstrip().upper().startswith("INSERT INTO EMBEDDINGS"):
            raise RuntimeError("Injected SQL insert failure after deletion")

    event.listen(database.engine.sync_engine, "before_cursor_execute", reject_insert)
    try:
        with pytest.raises(RuntimeError, match="Injected SQL"):
            await service.store_document(document, [DocumentChunk(index=0, content="replacement")], [[.2]], EmbeddingConfig())
    finally:
        event.remove(database.engine.sync_engine, "before_cursor_execute", reject_insert)
    async with database.factory() as session:
        assert await session.scalar(select(Embedding.content).where(Embedding.document_id == document.id)) == "original"
    with pytest.raises(service.DocumentValidationError):
        await service.store_document(document, chunks, [], EmbeddingConfig())


async def test_settings_database_constraint_and_duplicate_savepoint(database, owner):
    async with database.factory() as session:
        repo = SettingsRepository(session)
        await repo.create_default(owner.id)
        unrelated = User(email=f"{uuid4()}@example.invalid")
        session.add(unrelated)
        with pytest.raises(IntegrityError):
            await repo.create_default(owner.id)
        await session.commit()
        assert await session.get(User, unrelated.id) is not None
        with pytest.raises(IntegrityError):
            await session.execute(text("UPDATE user_settings SET chunk_overlap = chunk_size"))
        await session.rollback()
        value = await repo.get_by_user_id(owner.id)
        assert value.chunk_overlap < value.chunk_size


async def test_concurrent_settings_initialization(database, owner):
    async def initialize():
        async with database.factory() as session:
            result = await SettingsRepository(session).get_or_create(owner.id)
            await session.commit()
            return result.id
    identifiers = await asyncio.wait_for(asyncio.gather(*(initialize() for _ in range(6))), timeout=15)
    assert len(set(identifiers)) == 1


async def test_settings_lock_refreshes_stale_snapshot(database, owner):
    if database.dialect != "postgresql":
        pytest.skip("SELECT FOR UPDATE requires PostgreSQL")
    async with database.factory() as setup:
        await SettingsRepository(setup).get_or_create(owner.id)
        await setup.commit()
    async with database.factory() as first, database.factory() as second:
        # Deliberately cache an old value in the losing transaction's identity map.
        stale = await SettingsRepository(second).get_by_user_id(owner.id)
        assert stale.chunk_overlap == 200
        locked = await SettingsRepository(first).get_or_create(owner.id)
        locked.chunk_overlap = 800
        started = asyncio.Event()

        async def competing_update():
            started.set()
            return await SettingsService(second).update_settings(owner.id, SettingsUpdate(chunk_size=500))

        task = asyncio.create_task(competing_update())
        try:
            await started.wait()
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(asyncio.shield(task), timeout=.15)
            await first.commit()
            with pytest.raises(SettingsValidationError, match="chunk_overlap"):
                await asyncio.wait_for(task, timeout=5)
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            await second.rollback()
    async with database.factory() as session:
        current = await SettingsRepository(session).get_by_user_id(owner.id)
        assert (current.chunk_size, current.chunk_overlap) == (1000, 800)


async def test_concurrent_document_replacements(database, owner, storage):
    if database.dialect != "postgresql":
        pytest.skip("Document row locking requires PostgreSQL")
    document = await service.upload_document(b"content", "one.txt", "text/plain", owner.id)
    async def replace(value):
        await service.store_document(document, [DocumentChunk(index=i, content=value) for i in range(3)], [[.1]] * 3, EmbeddingConfig())
    await asyncio.wait_for(asyncio.gather(*(replace(str(i)) for i in range(4))), timeout=15)
    async with database.factory() as session:
        rows = (await session.scalars(select(Embedding).where(Embedding.document_id == document.id))).all()
        assert len(rows) == 3
        assert len({row.content for row in rows}) == 1


async def test_migrated_schema_and_downgrade(database):
    async with database.engine.connect() as connection:
        def inspect_schema(sync):
            schema = inspect(sync)
            assert "deleted_at" in {column["name"] for column in schema.get_columns("chat_sessions")}
            assert "ix_chat_sessions_deleted_at" in {index["name"] for index in schema.get_indexes("chat_sessions")}
            assert "uq_embeddings_document_chunk" in {constraint["name"] for constraint in schema.get_unique_constraints("embeddings")}
            assert "ck_user_settings_chunk_overlap" in {constraint["name"] for constraint in schema.get_check_constraints("user_settings")}
            assert any(key["referred_table"] == "documents" and key["options"].get("ondelete") == "CASCADE" for key in schema.get_foreign_keys("embeddings"))
        await connection.run_sync(inspect_schema)
    await asyncio.to_thread(command.downgrade, migration_config(database.migration_url), PREVIOUS)
    await asyncio.to_thread(command.upgrade, migration_config(database.migration_url), "head")


async def test_upgrade_repairs_duplicate_chunks_without_changing_other_sources(database, owner):
    config = migration_config(database.migration_url)
    await asyncio.to_thread(command.downgrade, config, PREVIOUS)
    async with database.factory() as session:
        document = Document(user_id=owner.id, filename="legacy.txt", storage_key="uploads/legacy.txt")
        website = Website(user_id=owner.id, url="https://example.invalid")
        session.add_all([document, website])
        await session.flush()
        for index, content in enumerate(["old", "new"]):
            session.add(Embedding(document_id=document.id, chunk_index=0, content=content,
                                  vector=[.1], model_name="test", updated_at=datetime(2026, 1, 1) + timedelta(days=index)))
            session.add(Embedding(website_id=website.id, chunk_index=0, content=content,
                                  vector=[.1], model_name="test"))
        await session.commit()
        document_id, website_id = document.id, website.id
    await asyncio.to_thread(command.upgrade, config, "head")
    async with database.factory() as session:
        assert (await session.scalars(select(Embedding.content).where(Embedding.document_id == document_id))).all() == ["new"]
        assert await session.scalar(select(func.count()).select_from(Embedding).where(Embedding.website_id == website_id)) == 2
        assert await session.get(User, owner.id) is not None


async def test_invalid_legacy_settings_stop_upgrade_before_schema_changes(database, owner):
    config = migration_config(database.migration_url)
    await asyncio.to_thread(command.downgrade, config, PREVIOUS)
    async with database.factory() as session:
        session.add(UserSettings(user_id=owner.id, chunk_size=100, chunk_overlap=100))
        await session.commit()
    with pytest.raises(RuntimeError, match="invalid chunk settings exist"):
        await asyncio.to_thread(command.upgrade, config, "head")
    async with database.engine.begin() as connection:
        columns = await connection.run_sync(lambda sync: inspect(sync).get_columns("chat_sessions"))
        assert "deleted_at" not in {column["name"] for column in columns}
        assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == PREVIOUS
        await connection.execute(text("UPDATE user_settings SET chunk_overlap = 20"))
    await asyncio.to_thread(command.upgrade, config, "head")

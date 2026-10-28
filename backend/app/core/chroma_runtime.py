"""Serialized initialization and additive recovery for the local Chroma store.

Chroma 0.6 publishes its shared System before startup migrations finish. Every
application client must enter through this module, from a worker thread.
"""

import logging
import sqlite3
from contextlib import closing
from pathlib import Path
from threading import RLock

logger = logging.getLogger(__name__)
_init_lock = RLock()


def _restore_missing_tenants(path: Path) -> None:
    """Restore only a lost tenant table in an otherwise migrated 0.6 schema.

    Replaying the old tenant migration would replace collections. Instead, recover
    tenant IDs from their existing databases without changing database/vector IDs.
    Unknown or more extensive corruption is left intact for operator recovery.
    """
    with closing(sqlite3.connect(path / "chroma.sqlite3", timeout=10)) as db, db:
        # Protect inspection and repair together against other writers.
        db.execute("BEGIN IMMEDIATE")
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "tenants" in tables:
            return
        if not {"migrations", "databases", "collections"}.issubset(tables):
            raise RuntimeError("Chroma schema requires operator recovery")
        applied = db.execute(
            "SELECT 1 FROM migrations WHERE dir='sysdb' AND version=4"
        ).fetchone()
        if applied is None:
            raise RuntimeError("Chroma tenant migration has not completed")
        db.execute("CREATE TABLE IF NOT EXISTS tenants (id TEXT PRIMARY KEY, UNIQUE (id))")
        db.execute("INSERT OR IGNORE INTO tenants (id) SELECT DISTINCT tenant_id FROM databases")


def _recover_defaults(settings, path: Path) -> None:
    import chromadb
    from chromadb.config import DEFAULT_DATABASE, DEFAULT_TENANT
    from chromadb.db.impl.sqlite import SqliteDB
    from chromadb.errors import NotFoundError, UniqueConstraintError

    admin = chromadb.AdminClient(settings=settings)
    # Use the pinned Chroma release's migration engine, never reset its storage
    # or clear the global System cache (other clients may still be using it).
    admin._system.instance(SqliteDB).initialize_migrations()
    _restore_missing_tenants(path)
    try:
        admin.get_tenant(DEFAULT_TENANT)
    except NotFoundError:
        try:
            admin.create_tenant(DEFAULT_TENANT)
        except UniqueConstraintError:
            pass
    try:
        admin.get_database(DEFAULT_DATABASE, tenant=DEFAULT_TENANT)
    except NotFoundError:
        # A replacement database gets a new ID. Never silently hide collections
        # that still reference a lost database record.
        with closing(sqlite3.connect(path / "chroma.sqlite3", timeout=10)) as db:
            orphan = db.execute(
                "SELECT 1 FROM collections WHERE database_id NOT IN "
                "(SELECT id FROM databases) LIMIT 1"
            ).fetchone()
        if orphan is not None:
            raise RuntimeError("Chroma database ownership requires operator recovery")
        try:
            admin.create_database(DEFAULT_DATABASE, tenant=DEFAULT_TENANT)
        except UniqueConstraintError:
            pass


def get_chroma_client(directory: str):
    import chromadb
    from chromadb.config import DEFAULT_DATABASE, DEFAULT_TENANT, Settings
    from chromadb.errors import NotFoundError

    path = Path(directory).expanduser().resolve()
    with _init_lock:
        path.mkdir(parents=True, exist_ok=True)
        settings = Settings(
            is_persistent=True, persist_directory=str(path), migrations="apply",
            anonymized_telemetry=False,
            chroma_product_telemetry_impl="app.core.telemetry.DisabledProductTelemetry",
            chroma_telemetry_impl="app.core.telemetry.DisabledProductTelemetry",
        )

        def connect():
            return chromadb.PersistentClient(
                path=str(path), settings=settings,
                tenant=DEFAULT_TENANT, database=DEFAULT_DATABASE,
            )

        try:
            return connect()
        except (ValueError, sqlite3.OperationalError, NotFoundError) as exc:
            message = str(exc).lower()
            if not isinstance(exc, NotFoundError) and not any(marker in message for marker in (
                "could not connect to tenant", "could not connect to database",
                "no such table: tenants",
            )):
                raise
            logger.warning("Repairing incomplete Chroma tenant initialization at %s", path)
            _recover_defaults(settings, path)
            return connect()  # One bounded retry; never substitute an empty store.

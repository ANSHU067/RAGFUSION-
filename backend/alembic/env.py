"""Alembic migration environment."""

import asyncio
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

import app.models.entities  # noqa: F401 - registers every model with Base.metadata
from alembic import context
from app.models.base import Base
from app.config.settings import get_settings
from app.db.session import to_async_database_url

config = context.config
if config.config_file_name and config.file_config.has_section("formatters"):
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def database_url() -> str:
    """Honor explicit test/tool URLs; CLI migrations use the API's settings."""
    return config.get_main_option("sqlalchemy.url") or to_async_database_url(get_settings().database_url)


def run_migrations_offline() -> None:
    """Run migrations without a database connection."""

    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def migrate(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations(url: str) -> None:
    engine = create_async_engine(url, poolclass=pool.NullPool)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(migrate)
    finally:
        await engine.dispose()


def run_migrations_online() -> None:
    """Support the async API driver and explicit synchronous test URLs."""
    if config.attributes.get("connection") is not None:
        migrate(config.attributes["connection"])
        return
    url = database_url()
    if make_url(url).get_dialect().is_async:
        asyncio.run(run_async_migrations(url))
    else:
        engine = create_engine(url, poolclass=pool.NullPool)
        try:
            with engine.connect() as connection:
                migrate(connection)
        finally:
            engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

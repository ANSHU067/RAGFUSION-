"""Verify the initial Alembic revision creates and removes every table."""

from __future__ import annotations

from sqlalchemy import create_engine, inspect, text

from alembic import command
from alembic.config import Config

EXPECTED_TABLES = {
    "alembic_version",
    "users",
    "documents",
    "websites",
    "youtube_sources",
    "chat_sessions",
    "messages",
    "settings",
    "embeddings",
}


def test_initial_migration_upgrade_and_downgrade(tmp_path) -> None:
    database_url = f"sqlite:///{tmp_path / 'migrations.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "head")
    engine = create_engine(database_url)
    assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())
    command.downgrade(config, "base")
    # Alembic retains its version bookkeeping table after a downgrade.
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    engine.dispose()


def test_recent_migrations_tolerate_preexisting_columns(tmp_path) -> None:
    """Recent revisions must resume when a column was created before a retry."""

    database_url = f"sqlite:///{tmp_path / 'partially_applied.db'}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "7efa7e63b3ce")
    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE chat_sessions ADD COLUMN deleted_at DATETIME"))
        connection.execute(
            text("ALTER TABLE users ADD COLUMN auth_version INTEGER DEFAULT 0 NOT NULL")
        )
        connection.execute(text("ALTER TABLE users ADD COLUMN bio VARCHAR(1000)"))
        connection.execute(text("ALTER TABLE users ADD COLUMN workspace VARCHAR(120)"))
        connection.execute(
            text("ALTER TABLE users ADD COLUMN avatar_color VARCHAR(16) DEFAULT 'slate' NOT NULL")
        )

    command.upgrade(config, "head")
    inspector = inspect(engine)
    assert {column["name"] for column in inspector.get_columns("chat_sessions")} >= {
        "deleted_at"
    }
    assert {column["name"] for column in inspector.get_columns("users")} >= {
        "auth_version",
        "bio",
        "workspace",
        "avatar_color",
    }
    engine.dispose()

"""Add chat deletion timestamp and enforce ingestion/settings invariants.

Revision ID: 20261005_0001
Revises: 7efa7e63b3ce
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20261005_0001"
down_revision = "7efa7e63b3ce"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    invalid = connection.scalar(sa.text(
        "SELECT count(*) FROM user_settings "
        "WHERE chunk_overlap < 0 OR chunk_overlap >= chunk_size"
    ))
    if invalid:
        raise RuntimeError(
            "Cannot apply storage integrity migration: invalid chunk settings exist. "
            "Correct chunk_overlap to be >= 0 and < chunk_size, then retry."
        )

    inspector = inspect(connection)
    existing_columns = [column["name"] for column in inspector.get_columns("chat_sessions")]
    if "deleted_at" not in existing_columns:
        op.add_column(
            "chat_sessions",
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )

    # The column may have been created by a partially applied/manual schema
    # change. Re-inspect after the conditional add before creating its index.
    inspector = inspect(connection)
    existing_indexes = {
        index["name"] for index in inspector.get_indexes("chat_sessions")
    }
    if "ix_chat_sessions_deleted_at" not in existing_indexes:
        op.create_index("ix_chat_sessions_deleted_at", "chat_sessions", ["deleted_at"])

    # Keep the most recently written SQL chunk on existing repeated ingestions.
    # NULL document_id rows belong to other source types and remain untouched.
    inspector = inspect(connection)
    existing_unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("embeddings")
        if constraint.get("name")
    }
    if "uq_embeddings_document_chunk" not in existing_unique_constraints:
        op.execute(sa.text("""
            DELETE FROM embeddings WHERE id IN (
                SELECT id FROM (
                    SELECT id, row_number() OVER (
                        PARTITION BY document_id, chunk_index
                        ORDER BY updated_at DESC, created_at DESC, id DESC
                    ) AS position
                    FROM embeddings WHERE document_id IS NOT NULL
                ) AS duplicates WHERE position > 1
            )
        """))
        with op.batch_alter_table("embeddings") as batch:
            batch.create_unique_constraint(
                "uq_embeddings_document_chunk", ["document_id", "chunk_index"]
            )

    inspector = inspect(connection)
    existing_check_constraints = {
        constraint["name"]
        for constraint in inspector.get_check_constraints("user_settings")
        if constraint.get("name")
    }
    if "ck_user_settings_chunk_overlap" not in existing_check_constraints:
        with op.batch_alter_table("user_settings") as batch:
            batch.create_check_constraint(
                "ck_user_settings_chunk_overlap",
                "chunk_overlap >= 0 AND chunk_overlap < chunk_size",
            )


def downgrade() -> None:
    with op.batch_alter_table("user_settings") as batch:
        batch.drop_constraint("ck_user_settings_chunk_overlap", type_="check")
    with op.batch_alter_table("embeddings") as batch:
        batch.drop_constraint("uq_embeddings_document_chunk", type_="unique")
    op.drop_index("ix_chat_sessions_deleted_at", table_name="chat_sessions")
    op.drop_column("chat_sessions", "deleted_at")

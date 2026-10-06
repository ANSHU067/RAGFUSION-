"""Add chat deletion timestamp and enforce ingestion/settings invariants.

Revision ID: 20261005_0001
Revises: 7efa7e63b3ce
"""

from alembic import op
import sqlalchemy as sa

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

    op.add_column("chat_sessions", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_chat_sessions_deleted_at", "chat_sessions", ["deleted_at"])

    # Keep the most recently written SQL chunk on existing repeated ingestions.
    # NULL document_id rows belong to other source types and remain untouched.
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
        batch.create_unique_constraint("uq_embeddings_document_chunk", ["document_id", "chunk_index"])
    with op.batch_alter_table("user_settings") as batch:
        batch.create_check_constraint(
            "ck_user_settings_chunk_overlap", "chunk_overlap >= 0 AND chunk_overlap < chunk_size"
        )


def downgrade() -> None:
    with op.batch_alter_table("user_settings") as batch:
        batch.drop_constraint("ck_user_settings_chunk_overlap", type_="check")
    with op.batch_alter_table("embeddings") as batch:
        batch.drop_constraint("uq_embeddings_document_chunk", type_="unique")
    op.drop_index("ix_chat_sessions_deleted_at", table_name="chat_sessions")
    op.drop_column("chat_sessions", "deleted_at")

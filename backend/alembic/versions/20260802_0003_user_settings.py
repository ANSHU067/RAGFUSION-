"""Add user_settings table for AI configuration.

Revision ID: 20260802_0003
Revises: 20260802_0002
Create Date: 2026-08-02
"""

import sqlalchemy as sa
from alembic import op

revision = "20260802_0003"
down_revision = "20260802_0002"
branch_labels = None
depends_on = None


llm_provider = sa.Enum(
    "openai",
    "anthropic",
    "ollama",
    "groq",
    "together",
    "custom",
    name="llmprovider",
    native_enum=False,
)
embedding_provider = sa.Enum(
    "openai",
    "huggingface",
    "cohere",
    "voyage",
    "ollama",
    "custom",
    name="embeddingprovider",
    native_enum=False,
)


def upgrade() -> None:
    op.create_table(
        "user_settings",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "provider",
            llm_provider,
            server_default="openai",
            nullable=False,
        ),
        sa.Column(
            "model_name", sa.String(255), server_default="gpt-4o-mini", nullable=False
        ),
        sa.Column(
            "embedding_provider",
            embedding_provider,
            server_default="openai",
            nullable=False,
        ),
        sa.Column(
            "embedding_model",
            sa.String(255),
            server_default="text-embedding-3-small",
            nullable=False,
        ),
        sa.Column("temperature", sa.Float(), server_default="0.7", nullable=False),
        sa.Column("top_k", sa.Integer(), server_default="5", nullable=False),
        sa.Column("max_tokens", sa.Integer(), server_default="2000", nullable=False),
        sa.Column("chunk_size", sa.Integer(), server_default="1000", nullable=False),
        sa.Column("chunk_overlap", sa.Integer(), server_default="200", nullable=False),
        sa.Column(
            "similarity_threshold", sa.Float(), server_default="0.7", nullable=False
        ),
        sa.Column(
            "reranking_enabled", sa.Boolean(), server_default=sa.true(), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", name="uq_user_settings_user"),
    )
    op.create_index("ix_user_settings_user_id", "user_settings", ["user_id"])


def downgrade() -> None:
    op.drop_table("user_settings")
    llm_provider.drop(op.get_bind(), checkfirst=True)
    embedding_provider.drop(op.get_bind(), checkfirst=True)

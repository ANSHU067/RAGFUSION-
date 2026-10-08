"""Persist account-wide token revocation versions.

Revision ID: 20261005_0002
Revises: 20261005_0001
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20261005_0002"
down_revision = "20261005_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = [column["name"] for column in inspector.get_columns("users")]
    if "auth_version" not in existing_columns:
        op.add_column(
            "users",
            sa.Column("auth_version", sa.Integer(), server_default="0", nullable=False),
        )


def downgrade() -> None:
    op.drop_column("users", "auth_version")

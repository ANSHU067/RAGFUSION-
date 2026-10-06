"""Persist account-wide token revocation versions.

Revision ID: 20261005_0002
Revises: 20261005_0001
"""
from alembic import op
import sqlalchemy as sa

revision = "20261005_0002"
down_revision = "20261005_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("auth_version", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("users", "auth_version")

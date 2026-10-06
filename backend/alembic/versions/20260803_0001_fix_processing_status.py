"""Fix legacy processing status values.

Revision ID: 20260803_0001
Revises: 20260801_0001
Create Date: 2026-08-03
"""

from alembic import op

revision = "20260803_0001"
down_revision = "20260801_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Update all 'processing' status values to 'pending'.

    The application now uses a more granular state machine:
    pending -> validating -> cleaning -> chunking -> embedding -> storing -> ready

    Legacy 'processing' values are mapped to 'pending' for backward compatibility.
    """
    # Update documents table
    op.execute(
        """
        UPDATE documents
        SET status = 'pending'
        WHERE status = 'processing'
        """
    )

    # Update websites table
    op.execute(
        """
        UPDATE websites
        SET status = 'pending'
        WHERE status = 'processing'
        """
    )

    # Update youtube_sources table
    op.execute(
        """
        UPDATE youtube_sources
        SET status = 'pending'
        WHERE status = 'processing'
        """
    )


def downgrade() -> None:
    """
    Revert pending status back to processing.

    This is a lossy operation as we cannot distinguish which 'pending'
    rows were originally 'processing'.
    """
    # Note: This downgrade is imperfect since we can't distinguish
    # between rows that were originally 'processing' vs 'pending'
    pass

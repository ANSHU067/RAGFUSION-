"""merge migration heads

Revision ID: 7efa7e63b3ce
Revises: 20260802_0003, 20260803_0001
Create Date: 2026-08-24 13:22:43.675947
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = '7efa7e63b3ce'
down_revision: Union[str, Sequence[str], None] = ('20260802_0003', '20260803_0001')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

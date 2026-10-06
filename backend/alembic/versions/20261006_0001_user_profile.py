"""Add validated editable profile fields without changing authentication state."""
from alembic import op
import sqlalchemy as sa

revision = '20261006_0001'
down_revision = '20261005_0002'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('bio', sa.String(1000), nullable=True))
    op.add_column('users', sa.Column('workspace', sa.String(120), nullable=True))
    op.add_column('users', sa.Column('avatar_color', sa.String(16), server_default='slate', nullable=False))


def downgrade():
    op.drop_column('users', 'avatar_color')
    op.drop_column('users', 'workspace')
    op.drop_column('users', 'bio')

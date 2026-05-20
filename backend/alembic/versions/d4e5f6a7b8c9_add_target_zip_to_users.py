"""add target_zip to users

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-20
"""

from alembic import op
import sqlalchemy as sa

revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('target_zip', sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('users', 'target_zip')

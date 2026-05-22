"""add email_verified to users

Revision ID: k1f2a3b4c5d6
Revises: j0e1f2a3b4c5
Create Date: 2026-05-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'k1f2a3b4c5d6'
down_revision = 'j0e1f2a3b4c5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='false'),
    )


def downgrade() -> None:
    op.drop_column('users', 'email_verified')

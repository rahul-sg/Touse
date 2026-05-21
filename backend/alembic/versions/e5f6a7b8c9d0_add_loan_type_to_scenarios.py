"""add loan_type to scenarios

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'e5f6a7b8c9d0'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'scenarios',
        sa.Column('loan_type', sa.String(20), nullable=True, server_default='conventional'),
    )


def downgrade() -> None:
    op.drop_column('scenarios', 'loan_type')

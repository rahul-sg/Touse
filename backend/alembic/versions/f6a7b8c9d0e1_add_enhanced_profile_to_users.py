"""add enhanced financial profile fields to users

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'f6a7b8c9d0e1'
down_revision = 'e5f6a7b8c9d0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('liquid_savings', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('brokerage_value', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('retirement_value', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('monthly_take_home', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'monthly_take_home')
    op.drop_column('users', 'retirement_value')
    op.drop_column('users', 'brokerage_value')
    op.drop_column('users', 'liquid_savings')

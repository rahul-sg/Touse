"""add home_type to zip_price_history

Phase 11 — type-aware forecasting. Each ZIP now carries one row per
(home_type, date), with home_type ∈ {'all', 'single_family', 'condo'}.

Existing rows are backfilled as 'all'. The next ETL run populates the
single_family and condo series alongside.

Revision ID: p6k7l8m9n0o1
Revises: o5j6k7l8m9n0
Create Date: 2026-05-24 22:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'p6k7l8m9n0o1'
down_revision = 'o5j6k7l8m9n0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'zip_price_history',
        sa.Column('home_type', sa.String(20), nullable=False, server_default='all'),
    )
    op.drop_constraint('uq_zip_price_history_zip_date', 'zip_price_history', type_='unique')
    op.create_unique_constraint(
        'uq_zip_price_history_zip_type_date',
        'zip_price_history',
        ['zip_code', 'home_type', 'date'],
    )
    op.create_index('ix_zip_price_home_type', 'zip_price_history', ['home_type'])


def downgrade() -> None:
    op.drop_index('ix_zip_price_home_type', table_name='zip_price_history')
    op.drop_constraint('uq_zip_price_history_zip_type_date', 'zip_price_history', type_='unique')
    op.create_unique_constraint(
        'uq_zip_price_history_zip_date',
        'zip_price_history',
        ['zip_code', 'date'],
    )
    op.drop_column('zip_price_history', 'home_type')

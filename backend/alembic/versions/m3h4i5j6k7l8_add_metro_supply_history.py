"""add metro_supply_history table

Stores monthly Zillow Research metro supply/demand indicators — active
inventory, new listings, mean days-on-market, % price cuts, median list price.
The biggest single missing dataset for short-term housing forecasting.

Revision ID: m3h4i5j6k7l8
Revises: l2g3b4c5d6e7
Create Date: 2026-05-23 21:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'm3h4i5j6k7l8'
down_revision = 'l2g3b4c5d6e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'metro_supply_history',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('metro', sa.String(120), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('invt_fs', sa.Float()),
        sa.Column('new_listings', sa.Float()),
        sa.Column('mean_doz_pending', sa.Float()),
        sa.Column('perc_price_cut', sa.Float()),
        sa.Column('median_list_price', sa.Float()),
        sa.UniqueConstraint('metro', 'date', name='uq_metro_supply_metro_date'),
    )
    op.create_index('ix_metro_supply_metro', 'metro_supply_history', ['metro'])
    op.create_index('ix_metro_supply_date', 'metro_supply_history', ['date'])


def downgrade() -> None:
    op.drop_index('ix_metro_supply_date', table_name='metro_supply_history')
    op.drop_index('ix_metro_supply_metro', table_name='metro_supply_history')
    op.drop_table('metro_supply_history')

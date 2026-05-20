"""add zillow supply signals to metro_price_history

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-20

Adds three nullable supply-signal columns sourced from Zillow Research free CSVs:
  - active_listings   (integer)
  - median_dom        (numeric 6,1) — median days on market
  - price_cut_pct     (numeric 5,2) — % of listings with a price cut
"""

from alembic import op
import sqlalchemy as sa

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'metro_price_history',
        sa.Column('active_listings', sa.Integer(), nullable=True),
    )
    op.add_column(
        'metro_price_history',
        sa.Column('median_dom', sa.Numeric(6, 1), nullable=True),
    )
    op.add_column(
        'metro_price_history',
        sa.Column('price_cut_pct', sa.Numeric(5, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('metro_price_history', 'price_cut_pct')
    op.drop_column('metro_price_history', 'median_dom')
    op.drop_column('metro_price_history', 'active_listings')

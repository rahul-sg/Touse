"""add median_rent to metro_supply_history (Zillow ZORI)

Revision ID: n4i5j6k7l8m9
Revises: m3h4i5j6k7l8
Create Date: 2026-05-24 21:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'n4i5j6k7l8m9'
down_revision = 'm3h4i5j6k7l8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('metro_supply_history', sa.Column('median_rent', sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column('metro_supply_history', 'median_rent')

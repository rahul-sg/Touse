"""add property_type / sqft / lot_sqft / year_built to listings_cache

Phase 10 — Zillow-style map filters. Existing rows leave these NULL; the next
ETL pass populates them.

Revision ID: o5j6k7l8m9n0
Revises: n4i5j6k7l8m9
Create Date: 2026-05-24 22:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'o5j6k7l8m9n0'
down_revision = 'n4i5j6k7l8m9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('listings_cache', sa.Column('property_type', sa.String(40), nullable=True))
    op.add_column('listings_cache', sa.Column('sqft', sa.Integer(), nullable=True))
    op.add_column('listings_cache', sa.Column('lot_sqft', sa.Integer(), nullable=True))
    op.add_column('listings_cache', sa.Column('year_built', sa.SmallInteger(), nullable=True))
    op.create_index('ix_listings_property_type', 'listings_cache', ['property_type'])


def downgrade() -> None:
    op.drop_index('ix_listings_property_type', table_name='listings_cache')
    op.drop_column('listings_cache', 'year_built')
    op.drop_column('listings_cache', 'lot_sqft')
    op.drop_column('listings_cache', 'sqft')
    op.drop_column('listings_cache', 'property_type')

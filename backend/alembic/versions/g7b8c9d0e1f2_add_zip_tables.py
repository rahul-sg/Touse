"""add zip_centroids and zip_price_history tables

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'g7b8c9d0e1f2'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'zip_centroids',
        sa.Column('zip_code', sa.String(10), primary_key=True),
        sa.Column('lat', sa.Float(), nullable=False),
        sa.Column('lng', sa.Float(), nullable=False),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state_code', sa.String(2), nullable=True),
        sa.Column('state_name', sa.String(50), nullable=True),
        sa.Column('county', sa.String(100), nullable=True),
    )
    op.create_index('ix_zip_centroids_lat_lng', 'zip_centroids', ['lat', 'lng'])

    op.create_table(
        'zip_price_history',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('zip_code', sa.String(10), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('median_value', sa.Float(), nullable=True),
        sa.Column('city', sa.String(100), nullable=True),
        sa.Column('state', sa.String(2), nullable=True),
        sa.Column('metro', sa.String(150), nullable=True),
        sa.UniqueConstraint('zip_code', 'date', name='uq_zip_price_history_zip_date'),
    )
    op.create_index('ix_zip_price_history_zip_code', 'zip_price_history', ['zip_code'])


def downgrade() -> None:
    op.drop_table('zip_price_history')
    op.drop_table('zip_centroids')

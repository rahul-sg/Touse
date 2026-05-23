"""add zip_lgbm_predictions table

One row per ZIP holding the latest global LightGBM 12-month price-growth
prediction. Written periodically by the train_global_lgbm Celery task and read
by the projection service to anchor the Prophet forecast endpoint.

Revision ID: l2g3b4c5d6e7
Revises: k1f2a3b4c5d6
Create Date: 2026-05-23 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'l2g3b4c5d6e7'
down_revision = 'k1f2a3b4c5d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'zip_lgbm_predictions',
        sa.Column('zip_code', sa.String(10), primary_key=True),
        sa.Column('model_version', sa.String(32), nullable=False),
        sa.Column('trained_at', sa.DateTime(), nullable=False),
        sa.Column('reference_month', sa.Date(), nullable=False),
        sa.Column('reference_price', sa.Float(), nullable=False),
        sa.Column('predicted_growth_12m', sa.Float(), nullable=False),
        sa.Column('predicted_endpoint_price', sa.Float(), nullable=False),
        sa.Column('data_points_used', sa.Integer(), nullable=False, server_default='0'),
    )


def downgrade() -> None:
    op.drop_table('zip_lgbm_predictions')

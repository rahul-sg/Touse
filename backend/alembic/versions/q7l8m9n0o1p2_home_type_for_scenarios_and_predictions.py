"""home_type for scenarios + predictions + forecasts

Carries the type-aware forecasting changes into the rest of the schema:
- scenarios.home_type           — picked by the user when creating a scenario
- zip_lgbm_predictions PK       — now (zip_code, home_type)
- zip_forecast_results          — gains home_type + uniq becomes (zip, type)

Existing rows backfill to 'all' (the combined SFR+condo index — what
everything used before this change).

Revision ID: q7l8m9n0o1p2
Revises: p6k7l8m9n0o1
Create Date: 2026-05-24 22:50:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'q7l8m9n0o1p2'
down_revision = 'p6k7l8m9n0o1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── scenarios ──
    op.add_column(
        'scenarios',
        sa.Column('home_type', sa.String(20), nullable=False, server_default='all'),
    )

    # ── zip_lgbm_predictions: PK becomes (zip_code, home_type) ──
    op.add_column(
        'zip_lgbm_predictions',
        sa.Column('home_type', sa.String(20), nullable=False, server_default='all'),
    )
    op.drop_constraint('zip_lgbm_predictions_pkey', 'zip_lgbm_predictions', type_='primary')
    op.create_primary_key(
        'zip_lgbm_predictions_pkey',
        'zip_lgbm_predictions',
        ['zip_code', 'home_type'],
    )

    # ── zip_forecast_results: add home_type, uniq becomes (zip, type) ──
    op.add_column(
        'zip_forecast_results',
        sa.Column('home_type', sa.String(20), nullable=False, server_default='all'),
    )
    op.drop_index('ix_zip_forecast_results_zip_code', table_name='zip_forecast_results')
    op.create_index(
        'ix_zip_forecast_zip_type',
        'zip_forecast_results',
        ['zip_code', 'home_type'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_zip_forecast_zip_type', table_name='zip_forecast_results')
    op.create_index(
        'ix_zip_forecast_results_zip_code',
        'zip_forecast_results',
        ['zip_code'],
        unique=True,
    )
    op.drop_column('zip_forecast_results', 'home_type')

    op.drop_constraint('zip_lgbm_predictions_pkey', 'zip_lgbm_predictions', type_='primary')
    op.create_primary_key('zip_lgbm_predictions_pkey', 'zip_lgbm_predictions', ['zip_code'])
    op.drop_column('zip_lgbm_predictions', 'home_type')

    op.drop_column('scenarios', 'home_type')

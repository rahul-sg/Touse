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

    # ── zip_forecast_results: create if missing, then add home_type ──
    # This table was not created in an earlier migration, so we create it here
    # (with home_type already included) if it doesn't exist yet.
    conn = op.get_bind()
    table_exists = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
            "WHERE table_name='zip_forecast_results')"
        )
    ).scalar()

    if not table_exists:
        op.create_table(
            'zip_forecast_results',
            sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
            sa.Column('zip_code', sa.String(10), nullable=False),
            sa.Column('home_type', sa.String(20), nullable=False, server_default='all'),
            sa.Column('model_version', sa.String(32), nullable=False),
            sa.Column('trained_at', sa.DateTime, nullable=False),
            sa.Column('current_value', sa.Float, nullable=True),
            sa.Column('forecast_12m_pct', sa.Float, nullable=True),
            sa.Column('data_points', sa.Integer, default=0),
            sa.Column('forecast_12m', sa.JSON, nullable=True),
        )
        op.create_index(
            'ix_zip_forecast_zip_type',
            'zip_forecast_results',
            ['zip_code', 'home_type'],
            unique=True,
        )
    else:
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

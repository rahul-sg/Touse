"""add forecast_realizations — track served forecasts vs realized prices

Every served projection inserts a placeholder row here (predicted_*, served_at,
horizon_end, actual_price=NULL). A monthly Celery task fills `actual_price`
once the horizon arrives. The Methodology / Forecast page surfaces the
per-(zip, home_type) realized MAPE so users see a live track record.

Revision ID: s9n0o1p2q3r4
Revises: r8m9n0o1p2q3
Create Date: 2026-05-25 04:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "s9n0o1p2q3r4"
down_revision = "r8m9n0o1p2q3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "forecast_realizations",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("zip_code", sa.String(10), nullable=False),
        sa.Column("home_type", sa.String(20), nullable=False, server_default="all"),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("served_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        # The horizon — when this prediction will be checkable.
        sa.Column("horizon_end", sa.Date, nullable=False),
        # What we predicted at serve time.
        sa.Column("current_price_at_serve", sa.Float, nullable=False),
        sa.Column("predicted_endpoint_price", sa.Float, nullable=False),
        # Filled in by realize_forecasts once horizon_end <= today and
        # zip_price_history has an observation for that month.
        sa.Column("actual_price", sa.Float, nullable=True),
        sa.Column("abs_pct_error", sa.Float, nullable=True),
        sa.Column("signed_pct_error", sa.Float, nullable=True),
        sa.Column("realized_at", sa.DateTime, nullable=True),
    )
    # Fast lookup for "most recent N realized forecasts for this (zip, home_type)".
    op.create_index(
        "ix_forecast_realizations_zip_type_horizon",
        "forecast_realizations",
        ["zip_code", "home_type", "horizon_end"],
    )
    # The realize_forecasts batch task scans by (horizon_end ≤ today AND actual_price IS NULL).
    op.create_index(
        "ix_forecast_realizations_horizon_pending",
        "forecast_realizations",
        ["horizon_end"],
        postgresql_where=sa.text("actual_price IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_forecast_realizations_horizon_pending", table_name="forecast_realizations")
    op.drop_index("ix_forecast_realizations_zip_type_horizon", table_name="forecast_realizations")
    op.drop_table("forecast_realizations")

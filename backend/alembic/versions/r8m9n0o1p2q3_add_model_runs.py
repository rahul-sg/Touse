"""add model_runs audit table

Every production training run of the global LightGBM panel inserts one row
here so the Methodology page can show users a live picture of how recently
the model was trained, how much data it saw, and what its held-out backtest
metrics looked like.

Revision ID: r8m9n0o1p2q3
Revises: q7l8m9n0o1p2
Create Date: 2026-05-25 04:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "r8m9n0o1p2q3"
down_revision = "q7l8m9n0o1p2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "model_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("model_version", sa.String(64), nullable=False),
        sa.Column("trained_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        # Inputs
        sa.Column("panel_rows", sa.BigInteger, nullable=False),
        sa.Column("train_rows", sa.BigInteger, nullable=False),
        sa.Column("feature_count", sa.Integer, nullable=False),
        sa.Column("zips_predicted", sa.Integer, nullable=False),
        # Cost
        sa.Column("train_seconds", sa.Float, nullable=False),
        # Backtest snapshot (optional — populated when a backtest is run alongside).
        # Per-home-type and per-seed metrics stored as JSON to keep the schema flat.
        sa.Column("backtest_mape_all", sa.Float, nullable=True),
        sa.Column("backtest_bias_all", sa.Float, nullable=True),
        sa.Column("backtest_per_type", sa.JSON, nullable=True),
        sa.Column("backtest_seeds", sa.JSON, nullable=True),
        # Free-form notes for the methodology page (e.g. "added rent feature").
        sa.Column("notes", sa.Text, nullable=True),
    )
    op.create_index("ix_model_runs_trained_at", "model_runs", ["trained_at"])


def downgrade() -> None:
    op.drop_index("ix_model_runs_trained_at", table_name="model_runs")
    op.drop_table("model_runs")

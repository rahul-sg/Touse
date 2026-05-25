"""Audit record for a single training run of the global LightGBM panel.

One row is inserted every time `train_lgbm.train_and_save_predictions` runs in
production. The Methodology page (and operators staring at /api/v1/methodology)
read this to understand how recent the served forecasts are, how much data
the model saw, and — when a backtest was run alongside — how it scored on
held-out months.
"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ModelRun(Base):
    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # Inputs the run actually saw
    panel_rows: Mapped[int] = mapped_column(BigInteger, nullable=False)
    train_rows: Mapped[int] = mapped_column(BigInteger, nullable=False)
    feature_count: Mapped[int] = mapped_column(Integer, nullable=False)
    zips_predicted: Mapped[int] = mapped_column(Integer, nullable=False)

    # Cost
    train_seconds: Mapped[float] = mapped_column(Float, nullable=False)

    # Backtest snapshot (optional)
    backtest_mape_all: Mapped[float | None] = mapped_column(Float, nullable=True)
    backtest_bias_all: Mapped[float | None] = mapped_column(Float, nullable=True)
    backtest_per_type: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    backtest_seeds: Mapped[list | None] = mapped_column(JSON, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

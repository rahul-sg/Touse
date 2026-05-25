"""A served forecast paired with its eventual realization.

Inserted (placeholder, actual_price=NULL) every time the projection service
serves a forecast for a (zip, home_type). A monthly Celery task fills the
actual price once horizon_end arrives. This powers a live per-ZIP track
record on the forecast / methodology pages — "our forecasts here have
averaged X% MAPE over the last 12 months."
"""
from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ForecastRealization(Base):
    __tablename__ = "forecast_realizations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    zip_code: Mapped[str] = mapped_column(String(10), nullable=False)
    home_type: Mapped[str] = mapped_column(String(20), nullable=False, default="all")
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    served_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    horizon_end: Mapped[date] = mapped_column(Date, nullable=False)

    current_price_at_serve: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_endpoint_price: Mapped[float] = mapped_column(Float, nullable=False)

    # Filled by realize_forecasts when horizon_end <= today.
    actual_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    abs_pct_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    signed_pct_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    realized_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

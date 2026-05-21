from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class ZipForecastResult(Base):
    """Cached Prophet 12-month home-value projection for a single ZIP code.

    One row per ZIP (zip_code is unique) — re-training upserts the row.
    """
    __tablename__ = "zip_forecast_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    zip_code: Mapped[str] = mapped_column(String(10), nullable=False, unique=True, index=True)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    current_value: Mapped[float | None] = mapped_column(Float)
    # Projected % change over the next 12 months (point estimate).
    forecast_12m_pct: Mapped[float | None] = mapped_column(Float)
    data_points: Mapped[int] = mapped_column(Integer, default=0)
    # JSON list of {month, price, lower, upper} — historical tail + 12 future months.
    forecast_12m: Mapped[list | None] = mapped_column(JSON)

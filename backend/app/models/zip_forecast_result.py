from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class ZipForecastResult(Base):
    """Cached Prophet 12-month home-value projection per (ZIP, home_type)."""
    __tablename__ = "zip_forecast_results"
    __table_args__ = (
        Index("ix_zip_forecast_zip_type", "zip_code", "home_type", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    zip_code: Mapped[str] = mapped_column(String(10), nullable=False)
    home_type: Mapped[str] = mapped_column(String(20), nullable=False, default="all", server_default="all")
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    trained_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    current_value: Mapped[float | None] = mapped_column(Float)
    forecast_12m_pct: Mapped[float | None] = mapped_column(Float)
    data_points: Mapped[int] = mapped_column(Integer, default=0)
    # JSON list of {month, price, lower, upper} — historical tail + 12 future months.
    forecast_12m: Mapped[list | None] = mapped_column(JSON)

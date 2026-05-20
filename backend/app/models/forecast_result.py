from datetime import date, datetime
from sqlalchemy import String, Date, Numeric, Integer, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class ForecastResult(Base):
    __tablename__ = "forecast_results"
    __table_args__ = (
        UniqueConstraint("metro_id", "model_version", name="uq_metro_model"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metro_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)  # e.g. "prophet_v1"
    trained_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    trend_3m: Mapped[float | None] = mapped_column(Numeric(8, 4))   # % change
    trend_12m: Mapped[float | None] = mapped_column(Numeric(8, 4))  # % change
    # JSON list of {month, price, lower, upper}
    forecast_12m: Mapped[dict | None] = mapped_column(JSON)
    top_drivers: Mapped[dict | None] = mapped_column(JSON)

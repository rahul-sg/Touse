from datetime import date
from sqlalchemy import String, Date, Numeric, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class MetroPriceHistory(Base):
    __tablename__ = "metro_price_history"
    __table_args__ = (
        UniqueConstraint("metro_id", "date", name="uq_metro_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metro_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    median_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    zillow_region_id: Mapped[str | None] = mapped_column(String(32))
    # Zillow supply signals (nullable — populated by separate ETL runs)
    active_listings: Mapped[int | None] = mapped_column(Integer, nullable=True)
    median_dom: Mapped[float | None] = mapped_column(Numeric(6, 1), nullable=True)
    price_cut_pct: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)

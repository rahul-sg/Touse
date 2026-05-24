from datetime import date
from sqlalchemy import String, Float, Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class ZipPriceHistory(Base):
    """Monthly Zillow ZHVI per (ZIP, home_type).

    home_type is one of 'all', 'single_family', 'condo' — Zillow doesn't
    publish a separate townhouse-only ZIP-level index.
    """
    __tablename__ = "zip_price_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    zip_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    home_type: Mapped[str] = mapped_column(String(20), nullable=False, default="all", index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    median_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(2), nullable=True)
    metro: Mapped[str | None] = mapped_column(String(150), nullable=True)

    __table_args__ = (
        UniqueConstraint("zip_code", "home_type", "date", name="uq_zip_price_history_zip_type_date"),
    )

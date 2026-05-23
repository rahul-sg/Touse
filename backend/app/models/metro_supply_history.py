from datetime import date
from sqlalchemy import String, Float, Date, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class MetroSupplyHistory(Base):
    """Monthly Zillow Research metro supply/demand indicators.

    `metro` is the normalized short-form Zillow metro name ("San Francisco, CA")
    that joins to zip_price_history.metro after normalization (long CBSA names
    are reduced via `etl/zillow_metro.py:normalize_metro`).
    """
    __tablename__ = "metro_supply_history"
    __table_args__ = (
        UniqueConstraint("metro", "date", name="uq_metro_supply_metro_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metro: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    invt_fs: Mapped[float | None] = mapped_column(Float)             # active for-sale inventory
    new_listings: Mapped[float | None] = mapped_column(Float)        # newly listed homes this month
    mean_doz_pending: Mapped[float | None] = mapped_column(Float)    # mean days on market before pending
    perc_price_cut: Mapped[float | None] = mapped_column(Float)      # % listings with a price cut
    median_list_price: Mapped[float | None] = mapped_column(Float)   # median list price

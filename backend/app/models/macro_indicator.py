from datetime import date
from sqlalchemy import String, Date, Numeric, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class MacroIndicator(Base):
    __tablename__ = "macro_indicators"
    __table_args__ = (
        UniqueConstraint("series_name", "geo_id", "date", name="uq_series_geo_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # series_name: mortgage_rate_30y | fed_funds_rate | cpi | housing_starts |
    #              unemployment | gdp_growth
    series_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # geo_id: "US" for national, state code (e.g. "CA") for state-level
    geo_id: Mapped[str] = mapped_column(String(16), nullable=False, default="US", index=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    value: Mapped[float] = mapped_column(Numeric(14, 6), nullable=False)
    source: Mapped[str | None] = mapped_column(String(16))  # FRED | BLS | BEA

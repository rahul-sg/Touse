from datetime import datetime
from sqlalchemy import String, Numeric, Integer, SmallInteger, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class ListingCache(Base):
    __tablename__ = "listings_cache"
    __table_args__ = (
        UniqueConstraint("external_id", "source", name="uq_listing_source"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="rapidapi")
    address: Mapped[str] = mapped_column(String(512), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    beds: Mapped[int | None] = mapped_column(SmallInteger)
    baths: Mapped[float | None] = mapped_column(Numeric(4, 1))
    lat: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    lng: Mapped[float] = mapped_column(Numeric(10, 7), nullable=False)
    zip_code: Mapped[str | None] = mapped_column(String(10), index=True)
    listing_url: Mapped[str | None] = mapped_column(String(1024))
    photo_url: Mapped[str | None] = mapped_column(String(1024))
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

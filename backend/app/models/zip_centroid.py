from sqlalchemy import String, Float, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class ZipCentroid(Base):
    __tablename__ = "zip_centroids"

    zip_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state_code: Mapped[str | None] = mapped_column(String(2), nullable=True)
    state_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    county: Mapped[str | None] = mapped_column(String(100), nullable=True)


# Composite index for spatial proximity queries (approximate bounding box)
Index("ix_zip_centroids_lat_lng", ZipCentroid.lat, ZipCentroid.lng)

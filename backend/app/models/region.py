from sqlalchemy import String, Integer, ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Region(Base):
    __tablename__ = "regions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metro_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    state_name: Mapped[str | None] = mapped_column(String(64))
    zip_codes: Mapped[list[str] | None] = mapped_column(ARRAY(String(10)))
    zillow_region_id: Mapped[str | None] = mapped_column(String(32), index=True)

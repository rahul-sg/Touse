import secrets
import string
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

_PUBLIC_ID_ALPHABET = string.ascii_letters + string.digits


def generate_public_id(length: int = 10) -> str:
    """Random base62 token used as the non-enumerable identifier in URLs."""
    return "".join(secrets.choice(_PUBLIC_ID_ALPHABET) for _ in range(length))


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Non-enumerable identifier exposed in URLs and the API (the integer PK stays internal).
    public_id: Mapped[str] = mapped_column(
        String(16), unique=True, index=True, nullable=False, default=generate_public_id
    )
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    scenario_type: Mapped[str] = mapped_column(String(10), nullable=False, default="buy")  # "buy" or "rent"
    # Financial inputs
    annual_income: Mapped[float | None] = mapped_column(Float, nullable=True)
    savings: Mapped[float | None] = mapped_column(Float, nullable=True)
    down_payment: Mapped[float | None] = mapped_column(Float, nullable=True)
    credit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_debt_car: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    monthly_debt_student: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    monthly_debt_credit: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    monthly_debt_other: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    zip_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    loan_type: Mapped[str | None] = mapped_column(String(20), nullable=True, default="conventional")
    # Type-aware forecasting: 'all' | 'single_family' | 'condo'
    home_type: Mapped[str] = mapped_column(String(20), nullable=False, default="all", server_default="all")
    # Cached affordability result
    cached_max_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    cached_monthly_payment: Mapped[float | None] = mapped_column(Float, nullable=True)
    cached_rate_used: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Boolean, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[int] = mapped_column(primary_key=True)
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
    # Cached affordability result
    cached_max_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    cached_monthly_payment: Mapped[float | None] = mapped_column(Float, nullable=True)
    cached_rate_used: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    # Financial profile (filled in step 2)
    annual_income: Mapped[float | None] = mapped_column(Float, nullable=True)
    savings: Mapped[float | None] = mapped_column(Float, nullable=True)
    down_payment: Mapped[float | None] = mapped_column(Float, nullable=True)
    credit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_debt_car: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    monthly_debt_student: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    monthly_debt_credit: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    monthly_debt_other: Mapped[float] = mapped_column(Float, default=0.0, server_default="0")
    zip_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

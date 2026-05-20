from sqlalchemy import String, Boolean, SmallInteger, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class PolicyFlag(Base):
    __tablename__ = "policy_flags"
    __table_args__ = (
        UniqueConstraint("state", "year", name="uq_state_year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    state: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    # 0 = no reform, 1 = partial (ADU/upzoning), 2 = major reform
    zoning_reform_score: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    first_time_buyer_credit_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    state_housing_bond_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    election_year: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(String(512))

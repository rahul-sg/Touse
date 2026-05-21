from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.scenario import Scenario

router = APIRouter(prefix="/api/v1/scenarios", tags=["scenarios"])


class ScenarioCreate(BaseModel):
    name: str
    scenario_type: str = "buy"  # "buy" or "rent"
    annual_income: float | None = None
    savings: float | None = None
    down_payment: float | None = None
    credit_score: int | None = None
    monthly_debt_car: float = 0
    monthly_debt_student: float = 0
    monthly_debt_credit: float = 0
    monthly_debt_other: float = 0
    zip_code: str | None = None
    loan_type: str | None = "conventional"
    cached_max_price: float | None = None
    cached_monthly_payment: float | None = None
    cached_rate_used: float | None = None


class ScenarioUpdate(BaseModel):
    name: str | None = None
    annual_income: float | None = None
    savings: float | None = None
    down_payment: float | None = None
    credit_score: int | None = None
    monthly_debt_car: float | None = None
    monthly_debt_student: float | None = None
    monthly_debt_credit: float | None = None
    monthly_debt_other: float | None = None
    zip_code: str | None = None
    loan_type: str | None = None
    cached_max_price: float | None = None
    cached_monthly_payment: float | None = None
    cached_rate_used: float | None = None


def _serialize(s: Scenario) -> dict:
    return {
        "id": s.id,
        "user_id": s.user_id,
        "name": s.name,
        "scenario_type": s.scenario_type,
        "annual_income": s.annual_income,
        "savings": s.savings,
        "down_payment": s.down_payment,
        "credit_score": s.credit_score,
        "monthly_debt_car": s.monthly_debt_car or 0,
        "monthly_debt_student": s.monthly_debt_student or 0,
        "monthly_debt_credit": s.monthly_debt_credit or 0,
        "monthly_debt_other": s.monthly_debt_other or 0,
        "zip_code": s.zip_code,
        "loan_type": s.loan_type or "conventional",
        "cached_max_price": s.cached_max_price,
        "cached_monthly_payment": s.cached_monthly_payment,
        "cached_rate_used": s.cached_rate_used,
        "is_active": s.is_active,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


@router.get("/user/{user_id}")
async def list_scenarios(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Scenario)
        .where(Scenario.user_id == user_id)
        .where(Scenario.is_active == True)
        .order_by(desc(Scenario.created_at))
    )
    return [_serialize(s) for s in result.scalars().all()]


@router.post("/user/{user_id}", status_code=201)
async def create_scenario(user_id: int, body: ScenarioCreate, db: AsyncSession = Depends(get_db)):
    scenario = Scenario(
        user_id=user_id,
        name=body.name,
        scenario_type=body.scenario_type,
        annual_income=body.annual_income,
        savings=body.savings,
        down_payment=body.down_payment,
        credit_score=body.credit_score,
        monthly_debt_car=body.monthly_debt_car,
        monthly_debt_student=body.monthly_debt_student,
        monthly_debt_credit=body.monthly_debt_credit,
        monthly_debt_other=body.monthly_debt_other,
        zip_code=body.zip_code,
        loan_type=body.loan_type or "conventional",
        cached_max_price=body.cached_max_price,
        cached_monthly_payment=body.cached_monthly_payment,
        cached_rate_used=body.cached_rate_used,
    )
    db.add(scenario)
    await db.commit()
    await db.refresh(scenario)
    return _serialize(scenario)


@router.put("/{scenario_id}")
async def update_scenario(scenario_id: int, body: ScenarioUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Scenario).where(Scenario.id == scenario_id))
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    for field, val in body.model_dump(exclude_none=True).items():
        setattr(scenario, field, val)
    await db.commit()
    await db.refresh(scenario)
    return _serialize(scenario)


@router.delete("/{scenario_id}", status_code=204)
async def delete_scenario(scenario_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Scenario).where(Scenario.id == scenario_id))
    scenario = result.scalar_one_or_none()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    scenario.is_active = False
    await db.commit()

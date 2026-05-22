from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel
from app.limiter import limiter
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.affordability import calculate_affordability

router = APIRouter(tags=["affordability"])

VALID_LOAN_TYPES = {"conventional", "fha", "va", "usda", "arm_5_1", "jumbo"}


class AffordabilityRequest(BaseModel):
    annual_income: float
    savings: float
    monthly_debt: float
    credit_score: int
    down_payment: float
    zip_code: str
    loan_type: str = "conventional"


@router.post("/affordability")
@limiter.limit("30/minute")
async def get_affordability(
    request: Request,
    body: AffordabilityRequest,
    db: AsyncSession = Depends(get_db),
):
    if body.loan_type not in VALID_LOAN_TYPES:
        body.loan_type = "conventional"
    return await calculate_affordability(body, db)

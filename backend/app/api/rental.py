from fastapi import APIRouter, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(tags=["rental"])
limiter = Limiter(key_func=get_remote_address)


class RentalAffordabilityRequest(BaseModel):
    annual_income: float
    savings: float
    monthly_debt_car: float = 0
    monthly_debt_student: float = 0
    monthly_debt_credit: float = 0
    monthly_debt_other: float = 0
    credit_score: int = 700
    zip_code: str = ""


@router.post("/api/v1/rental-affordability")
@limiter.limit("30/minute")
async def get_rental_affordability(request: Request, body: RentalAffordabilityRequest):
    gross_monthly = body.annual_income / 12
    total_monthly_debt = (
        body.monthly_debt_car + body.monthly_debt_student +
        body.monthly_debt_credit + body.monthly_debt_other
    )

    # Rule 1: 30% of gross income toward housing
    max_by_income = gross_monthly * 0.30

    # Rule 2: Total DTI 36% — back-end limit
    max_by_dti = max(0.0, gross_monthly * 0.36 - total_monthly_debt)

    max_monthly_rent = round(min(max_by_income, max_by_dti))

    # Conservative recommendation: 85% of max (leave buffer)
    recommended_rent = round(max_monthly_rent * 0.85)

    # Savings adequacy: 3 months of estimated living expenses (rent * 3 as proxy)
    months_of_rent_in_savings = round(body.savings / max_monthly_rent, 1) if max_monthly_rent > 0 else 0
    savings_adequate = months_of_rent_in_savings >= 2  # 2 months deposit + buffer is typical

    # First/last + security deposit estimate
    move_in_cost = round(max_monthly_rent * 3)  # first + last + security

    # Annual rent cost vs. estimated buy cost (rough)
    annual_rent_cost = max_monthly_rent * 12

    # Credit score tier label
    if body.credit_score >= 760:
        credit_label = "Excellent"
    elif body.credit_score >= 700:
        credit_label = "Good"
    elif body.credit_score >= 660:
        credit_label = "Fair"
    else:
        credit_label = "Below Average"

    # Rent-to-income ratio check
    dti_ratio = round((total_monthly_debt / gross_monthly) * 100, 1) if gross_monthly > 0 else 0

    return {
        "max_monthly_rent": max_monthly_rent,
        "recommended_monthly_rent": recommended_rent,
        "move_in_cost_estimate": move_in_cost,
        "months_of_rent_in_savings": months_of_rent_in_savings,
        "savings_adequate_for_move_in": savings_adequate,
        "annual_rent_cost": annual_rent_cost,
        "existing_dti_pct": dti_ratio,
        "credit_label": credit_label,
        "total_monthly_debt": round(total_monthly_debt),
        "gross_monthly_income": round(gross_monthly),
    }

"""
Readiness score endpoint.

Computes a 0-100 readiness score from a scenario's financial data.
Improvements over the old client-side version:
  - Uses cached_max_price as the down payment target (not a hardcoded $450K)
  - Tightens DTI ceiling from 36% → 32% when rate_used > 6.5%
  - Uses liquid_savings for the cushion component when provided (Phase 4)
"""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1", tags=["readiness"])


class ReadinessRequest(BaseModel):
    annual_income: float
    savings: float = 0
    down_payment: float = 0
    credit_score: int = 620
    monthly_debt_car: float = 0
    monthly_debt_student: float = 0
    monthly_debt_credit: float = 0
    monthly_debt_other: float = 0
    cached_max_price: float | None = None
    rate_used: float | None = None
    liquid_savings: float | None = None  # Phase 4: when net-worth breakdown available


@router.post("/readiness")
async def compute_readiness(body: ReadinessRequest):
    gross_monthly = body.annual_income / 12 if body.annual_income > 0 else 1
    total_debt = (
        body.monthly_debt_car
        + body.monthly_debt_student
        + body.monthly_debt_credit
        + body.monthly_debt_other
    )
    dti_ratio = total_debt / gross_monthly

    # Rate-adjusted DTI ceiling: tighten at 7%+ rates
    rate = body.rate_used or 0.0
    dti_ceiling = 0.32 if rate > 6.5 else 0.36
    dti_pts = max(0, round(35 * (1 - dti_ratio / dti_ceiling)))

    # Down payment % against actual target price, not a hardcoded number
    target_price = body.cached_max_price if body.cached_max_price and body.cached_max_price > 0 else 450_000
    dp_pct = body.down_payment / target_price
    dp_pts = min(25, round(25 * dp_pct / 0.20))

    # Credit score tiers
    cs = body.credit_score
    if cs >= 760:
        credit_pts, credit_label = 25, "Excellent"
    elif cs >= 700:
        credit_pts, credit_label = 20, "Good"
    elif cs >= 660:
        credit_pts, credit_label = 13, "Fair"
    elif cs >= 620:
        credit_pts, credit_label = 7, "Poor"
    else:
        credit_pts, credit_label = 3, "Very Poor"

    # Savings cushion — liquid_savings only when the net-worth breakdown is available
    liquid = body.liquid_savings if body.liquid_savings is not None else body.savings
    monthly_cost = gross_monthly * 0.60
    cushion_months = liquid / monthly_cost if monthly_cost > 0 else 0
    cushion_pts = min(15, round(15 * cushion_months / 6))

    score = min(100, dti_pts + dp_pts + credit_pts + cushion_pts)

    actions: list[str] = []
    if dti_pts < 25:
        actions.append(
            f"Reduce monthly debt — DTI is {round(dti_ratio * 100)}%, "
            f"aim for under {round(dti_ceiling * 100)}%"
            + (" (tighter threshold at current rates)" if rate > 6.5 else "")
        )
    if dp_pts < 20:
        actions.append(
            f"Grow your down payment — currently {round(dp_pct * 100, 1)}% "
            f"of your ${int(target_price):,} target, aim for 10–20%"
        )
    if credit_pts < 20:
        actions.append(f"Improve credit score — currently {cs} ({credit_label}), aim for 700+")
    if cushion_pts < 10:
        actions.append(
            f"Build your savings cushion — {cushion_months:.1f} months of expenses, aim for 3–6 months"
        )

    return {
        "score": score,
        "components": {
            "dti_pts": dti_pts,
            "dp_pts": dp_pts,
            "credit_pts": credit_pts,
            "cushion_pts": cushion_pts,
        },
        "dti_ratio_pct": round(dti_ratio * 100, 1),
        "dti_ceiling_pct": round(dti_ceiling * 100),
        "dp_pct": round(dp_pct * 100, 1),
        "cushion_months": round(cushion_months, 1),
        "credit_label": credit_label,
        "rate_used": rate,
        "target_price": target_price,
        "actions": actions,
    }

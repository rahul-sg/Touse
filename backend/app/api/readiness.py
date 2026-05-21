"""
Readiness score endpoint.

Computes a 0-100 readiness score from five components:
  dti_pts (30)  — debt-to-income health
  dp_pts  (20)  — down payment % of target price
  credit_pts (20) — credit score tier
  cushion_pts (15) — liquid savings runway
  market_fit_pts (15) — how well max_price aligns with ZIP median (Phase 6)

When no ZIP data is available, the four-component raw max is 85 and is
scaled to 100 so the score stays comparable.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.zip_price_history import ZipPriceHistory

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
    liquid_savings: float | None = None  # Phase 4
    target_zip: str | None = None        # Phase 6


async def _get_zip_median(zip_code: str, db: AsyncSession) -> float | None:
    row = await db.scalar(
        select(ZipPriceHistory.median_value)
        .where(
            ZipPriceHistory.zip_code == zip_code,
            ZipPriceHistory.median_value.isnot(None),
        )
        .order_by(desc(ZipPriceHistory.date))
        .limit(1)
    )
    return float(row) if row is not None else None


def _market_fit(max_price: float, median: float) -> tuple[int, str]:
    ratio = max_price / median
    if ratio >= 1.10:
        return 15, "Strong"
    if ratio >= 1.00:
        return 12, "Good"
    if ratio >= 0.90:
        return 8, "Fair"
    if ratio >= 0.75:
        return 4, "Tight"
    return 1, "Very tight"


@router.post("/readiness")
async def compute_readiness(body: ReadinessRequest, db: AsyncSession = Depends(get_db)):
    gross_monthly = body.annual_income / 12 if body.annual_income > 0 else 1
    total_debt = (
        body.monthly_debt_car
        + body.monthly_debt_student
        + body.monthly_debt_credit
        + body.monthly_debt_other
    )
    dti_ratio = total_debt / gross_monthly

    rate = body.rate_used or 0.0
    dti_ceiling = 0.32 if rate > 6.5 else 0.36
    dti_pts = max(0, round(30 * (1 - dti_ratio / dti_ceiling)))

    target_price = body.cached_max_price if body.cached_max_price and body.cached_max_price > 0 else 450_000
    dp_pct = body.down_payment / target_price
    dp_pts = min(20, round(20 * dp_pct / 0.20))

    cs = body.credit_score
    if cs >= 760:
        credit_pts, credit_label = 20, "Excellent"
    elif cs >= 700:
        credit_pts, credit_label = 16, "Good"
    elif cs >= 660:
        credit_pts, credit_label = 10, "Fair"
    elif cs >= 620:
        credit_pts, credit_label = 5, "Poor"
    else:
        credit_pts, credit_label = 2, "Very Poor"

    liquid = body.liquid_savings if body.liquid_savings is not None else body.savings
    monthly_cost = gross_monthly * 0.60
    cushion_months = liquid / monthly_cost if monthly_cost > 0 else 0
    cushion_pts = min(15, round(15 * cushion_months / 6))

    # Phase 6 — market fit
    market_median: float | None = None
    market_fit_pts: int = 0
    market_fit_label: str | None = None
    market_fit_ratio_pct: float | None = None
    has_market_data = False

    if body.target_zip:
        market_median = await _get_zip_median(body.target_zip, db)
        if market_median and market_median > 0:
            has_market_data = True
            market_fit_pts, market_fit_label = _market_fit(target_price, market_median)
            market_fit_ratio_pct = round(target_price / market_median * 100, 1)

    raw = dti_pts + dp_pts + credit_pts + cushion_pts + market_fit_pts
    if has_market_data:
        score = min(100, raw)
    else:
        # Scale 4-component max (85) to 100
        four_raw = dti_pts + dp_pts + credit_pts + cushion_pts
        score = min(100, round(four_raw * 100 / 85))
        raw = score  # expose scaled value

    actions: list[str] = []
    if dti_pts < 20:
        actions.append(
            f"Reduce monthly debt — DTI is {round(dti_ratio * 100)}%, "
            f"aim for under {round(dti_ceiling * 100)}%"
            + (" (tighter threshold at current rates)" if rate > 6.5 else "")
        )
    if dp_pts < 14:
        actions.append(
            f"Grow your down payment — currently {round(dp_pct * 100, 1)}% "
            f"of your ${int(target_price):,} target, aim for 10–20%"
        )
    if credit_pts < 16:
        actions.append(f"Improve credit score — currently {cs} ({credit_label}), aim for 700+")
    if cushion_pts < 10:
        actions.append(
            f"Build your savings cushion — {cushion_months:.1f} months of expenses, aim for 3–6 months"
        )
    if has_market_data and market_fit_pts < 8 and market_median:
        actions.append(
            f"Budget is tight for ZIP {body.target_zip} — "
            f"median home is ${int(market_median):,}, "
            f"your max is ${int(target_price):,} ({market_fit_ratio_pct}% of median)"
        )

    return {
        "score": score,
        "components": {
            "dti_pts": dti_pts,
            "dp_pts": dp_pts,
            "credit_pts": credit_pts,
            "cushion_pts": cushion_pts,
            "market_fit_pts": market_fit_pts,
        },
        "dti_ratio_pct": round(dti_ratio * 100, 1),
        "dti_ceiling_pct": round(dti_ceiling * 100),
        "dp_pct": round(dp_pct * 100, 1),
        "cushion_months": round(cushion_months, 1),
        "credit_label": credit_label,
        "rate_used": rate,
        "target_price": target_price,
        "market_median": market_median,
        "market_fit_label": market_fit_label,
        "market_fit_ratio_pct": market_fit_ratio_pct,
        "actions": actions,
    }

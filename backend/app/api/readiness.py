"""
Readiness score endpoint.

Buy scenarios are scored on five dimensions (100 pts total):
  Debt-to-income 30 · Down payment 20 · Credit 20 · Cushion 15 · Market fit 15
Rent scenarios use a four-dimension model (100 pts total):
  Debt-to-income 35 · Rent burden 25 · Credit 20 · Cushion 20

DTI is forward-looking — it includes the projected monthly housing payment, not
just the applicant's existing debt — so the score reflects life *after* the
purchase/move, not before it. The overall score is earned / possible × 100, so
omitting a dimension (e.g. no ZIP data for market fit) never distorts it.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.zip_price_history import ZipPriceHistory
from app.services.affordability import _get_current_rate

router = APIRouter(prefix="/api/v1", tags=["readiness"])


class ReadinessRequest(BaseModel):
    scenario_type: str = "buy"  # "buy" | "rent"
    annual_income: float
    savings: float = 0
    down_payment: float = 0
    credit_score: int = 620
    monthly_debt_car: float = 0
    monthly_debt_student: float = 0
    monthly_debt_credit: float = 0
    monthly_debt_other: float = 0
    cached_max_price: float | None = None        # home price (buy) | max rent (rent)
    cached_monthly_payment: float | None = None  # mortgage P&I+PMI (buy) | planned rent (rent)
    rate_used: float | None = None
    liquid_savings: float | None = None
    target_zip: str | None = None


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


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


def _credit_tier(score: int) -> tuple[float, str]:
    """Return (fraction 0-1, label) for a credit score."""
    if score >= 760:
        return 1.00, "Excellent"
    if score >= 700:
        return 0.80, "Good"
    if score >= 660:
        return 0.50, "Fair"
    if score >= 620:
        return 0.25, "Poor"
    return 0.10, "Very Poor"


def _market_fit(home_price: float, median: float) -> tuple[float, str]:
    """Return (fraction 0-1, label) for how a budget aligns with the ZIP median."""
    ratio = home_price / median
    if ratio >= 1.10:
        return 1.00, "Strong"
    if ratio >= 1.00:
        return 0.80, "Good"
    if ratio >= 0.90:
        return 0.55, "Fair"
    if ratio >= 0.75:
        return 0.28, "Tight"
    return 0.08, "Very tight"


def _amortized_payment(principal: float, annual_rate_pct: float, years: int = 30) -> float:
    r = annual_rate_pct / 100 / 12
    n = years * 12
    if r == 0:
        return principal / n if n else 0.0
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)


@router.post("/readiness")
async def compute_readiness(body: ReadinessRequest, db: AsyncSession = Depends(get_db)):
    gross_monthly = body.annual_income / 12 if body.annual_income > 0 else 1.0
    existing_debt = (
        body.monthly_debt_car
        + body.monthly_debt_student
        + body.monthly_debt_credit
        + body.monthly_debt_other
    )
    liquid = body.liquid_savings if body.liquid_savings is not None else body.savings
    is_rent = body.scenario_type == "rent"

    # Use the live mortgage rate when the caller didn't supply one — never 0.
    rate_pct = body.rate_used if body.rate_used else round(await _get_current_rate(db) * 100, 3)

    components: list[dict] = []
    actions: list[str] = []
    market_median: float | None = None
    market_fit_label: str | None = None
    market_fit_ratio_pct: float | None = None

    if is_rent:
        # Planned rent = the recommended rent the rental engine produced.
        rent = body.cached_monthly_payment or body.cached_max_price or 0.0

        # 1. DTI 35 — existing debt + rent vs income
        back_end = (existing_debt + rent) / gross_monthly
        dti_pts = round(35 * _clamp((0.50 - back_end) / (0.50 - 0.36)))
        components.append({"label": "Debt-to-income", "points": dti_pts, "max": 35})
        if dti_pts < 24:
            actions.append(
                f"Debt plus rent would be {round(back_end * 100)}% of income — "
                f"landlords typically look for under 40%."
            )

        # 2. Rent burden 25 — the 30%-of-income rule
        burden = rent / gross_monthly
        burden_pts = round(25 * _clamp((0.40 - burden) / (0.40 - 0.25)))
        components.append({"label": "Rent burden", "points": burden_pts, "max": 25})
        if burden_pts < 17:
            actions.append(
                f"Rent would be {round(burden * 100)}% of gross income — "
                f"aim for 30% or less for comfortable cash flow."
            )

        # 3. Credit 20
        credit_frac, credit_label = _credit_tier(body.credit_score)
        components.append({"label": "Credit score", "points": round(20 * credit_frac), "max": 20})
        if credit_frac < 0.80:
            actions.append(
                f"Improve your credit — currently {body.credit_score} ({credit_label}); "
                f"700+ eases rental approval."
            )

        # 4. Cushion 20 — months of rent saved (move-in costs + reserve)
        months_saved = liquid / rent if rent > 0 else 0.0
        cushion_pts = round(20 * _clamp(months_saved / 6))
        components.append({"label": "Savings cushion", "points": cushion_pts, "max": 20})
        if cushion_pts < 13:
            actions.append(
                f"You have {months_saved:.1f} months of rent saved — aim for 6 to cover "
                f"first/last/deposit plus an emergency reserve."
            )

        dti_ratio_pct = round(back_end * 100, 1)
        dti_ceiling_pct = 50

    else:
        home_price = body.cached_max_price or 0.0
        # Projected mortgage payment: prefer the affordability engine's figure
        # (it already includes PMI / loan-type effects); otherwise amortize.
        if body.cached_monthly_payment:
            housing_payment = body.cached_monthly_payment
        elif home_price > 0:
            housing_payment = _amortized_payment(
                max(0.0, home_price - body.down_payment), rate_pct
            )
        else:
            housing_payment = 0.0

        # 1. DTI 30 — forward-looking: existing debt + the projected mortgage
        good, ceil = (0.28, 0.42) if rate_pct > 6.5 else (0.30, 0.45)
        back_end = (existing_debt + housing_payment) / gross_monthly
        dti_pts = round(30 * _clamp((ceil - back_end) / (ceil - good)))
        components.append({"label": "Debt-to-income", "points": dti_pts, "max": 30})
        if dti_pts < 20:
            actions.append(
                f"Debt plus the projected mortgage is {round(back_end * 100)}% of income — "
                f"aim for under {round(ceil * 100)}%"
                + (" (tighter at current rates)" if rate_pct > 6.5 else "")
                + "."
            )

        # 2. Down payment 20 — % of home price, 20% target
        dp_pct = body.down_payment / home_price if home_price > 0 else 0.0
        dp_pts = round(20 * _clamp(dp_pct / 0.20))
        components.append({"label": "Down payment", "points": dp_pts, "max": 20})
        if dp_pts < 14:
            actions.append(
                f"Down payment is {round(dp_pct * 100, 1)}% of a ${int(home_price):,} home — "
                f"aim for 20% to drop PMI."
            )

        # 3. Credit 20
        credit_frac, credit_label = _credit_tier(body.credit_score)
        components.append({"label": "Credit score", "points": round(20 * credit_frac), "max": 20})
        if credit_frac < 0.80:
            actions.append(
                f"Improve your credit — currently {body.credit_score} ({credit_label}); "
                f"aim for 700+ for better rates."
            )

        # 4. Cushion 15 — reserves left AFTER the down payment, in months of payment
        reserves = max(0.0, liquid - body.down_payment)
        months_saved = reserves / housing_payment if housing_payment > 0 else 0.0
        cushion_pts = round(15 * _clamp(months_saved / 6))
        components.append({"label": "Savings cushion", "points": cushion_pts, "max": 15})
        if cushion_pts < 10:
            actions.append(
                f"After the down payment you'd have {months_saved:.1f} months of payments "
                f"in reserve — aim for 6."
            )

        # 5. Market fit 15 — home price vs ZIP median (only when ZIP data exists)
        if body.target_zip:
            market_median = await _get_zip_median(body.target_zip, db)
        if market_median and market_median > 0 and home_price > 0:
            mfit_frac, market_fit_label = _market_fit(home_price, market_median)
            market_fit_ratio_pct = round(home_price / market_median * 100, 1)
            components.append({
                "label": "Market fit", "points": round(15 * mfit_frac), "max": 15,
            })
            if mfit_frac < 0.55:
                actions.append(
                    f"Budget is tight for ZIP {body.target_zip} — median home is "
                    f"${int(market_median):,}, your max ${int(home_price):,} "
                    f"({market_fit_ratio_pct}% of median)."
                )

        dti_ratio_pct = round(back_end * 100, 1)
        dti_ceiling_pct = round(ceil * 100)

    earned = sum(c["points"] for c in components)
    possible = sum(c["max"] for c in components)
    score = round(earned / possible * 100) if possible else 0

    return {
        "score": score,
        "scenario_type": body.scenario_type,
        "components": components,
        "credit_label": credit_label,
        "dti_ratio_pct": dti_ratio_pct,
        "dti_ceiling_pct": dti_ceiling_pct,
        "rate_used": rate_pct,
        "market_median": market_median,
        "market_fit_label": market_fit_label,
        "market_fit_ratio_pct": market_fit_ratio_pct,
        "actions": actions,
    }

"""
Now vs Wait comparison endpoint.

Computes affordability at today's rate vs after N months of additional saving,
across three rate scenarios (flat / down 0.5% / up 0.5%).
"""
from fastapi import APIRouter, Request, Depends
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.affordability import _get_current_rate, _credit_score_premium
from app.services.loan_calculators import LOAN_CALCULATORS, calc_conventional

router = APIRouter(prefix="/api/v1", tags=["compare"])
limiter = Limiter(key_func=get_remote_address)

VALID_LOAN_TYPES = {"conventional", "fha", "va", "usda", "arm_5_1", "jumbo"}


class CompareRequest(BaseModel):
    annual_income: float
    monthly_debt: float
    credit_score: int
    down_payment: float
    savings: float
    zip_code: str = ""
    loan_type: str = "conventional"
    monthly_savings: float          # how much they save per month
    wait_months: int = 12


class _FakeBody:
    """Minimal duck-type to reuse loan calculators without a full Pydantic model."""
    def __init__(self, annual_income, monthly_debt, credit_score, down_payment, savings):
        self.annual_income = annual_income
        self.monthly_debt = monthly_debt
        self.credit_score = credit_score
        self.down_payment = down_payment
        self.savings = savings


def _run_calc(body: _FakeBody, base_rate: float, credit_premium: float, loan_type: str) -> dict:
    calculator = LOAN_CALCULATORS.get(loan_type, calc_conventional)
    return calculator(body, base_rate, credit_premium)


def _build_scenario(annual_income, monthly_debt, credit_score, down_payment, savings,
                    base_rate, credit_premium, loan_type, rate_offset=0.0):
    body = _FakeBody(annual_income, monthly_debt, credit_score, down_payment, savings)
    result = _run_calc(body, base_rate + rate_offset, credit_premium, loan_type)
    return {
        "max_price": result["max_price"],
        "monthly_payment": result["monthly_payment"],
        "rate_used": result["rate_used"],
        "down_payment": round(down_payment),
    }


def _make_recommendation(price_delta: int, rate: float, monthly_savings: float) -> tuple[str, list[str]]:
    factors: list[str] = []
    score = 0  # positive = wait, negative = buy now

    # Savings impact
    if price_delta > 30_000:
        factors.append(f"Saving {int(monthly_savings):,}/mo adds ${price_delta:,} to your budget — a meaningful gain.")
        score += 2
    elif price_delta > 10_000:
        factors.append(f"Saving grows your budget by ${price_delta:,} — a modest but real improvement.")
        score += 1
    else:
        factors.append(f"The savings gain (${price_delta:,}) is small — timing matters more than saving here.")
        score -= 1

    # Rate environment
    if rate > 7.0:
        factors.append("Rates are elevated. If they fall, waiting could unlock significantly more buying power.")
        score += 1
    elif rate < 5.5:
        factors.append("Rates are relatively low — locking in now protects against future increases.")
        score -= 2
    else:
        factors.append("Rates are moderate. The rate direction matters more than the current level.")

    # Monthly savings adequacy
    if monthly_savings < 500:
        factors.append("Your monthly savings rate is low — the financial gap between now and waiting is small.")
        score -= 1

    if score >= 2:
        rec = "wait"
    elif score <= -1:
        rec = "buy_now"
    else:
        rec = "neutral"

    return rec, factors


@router.post("/compare/now-vs-wait")
@limiter.limit("20/minute")
async def compare_now_vs_wait(
    request: Request,
    body: CompareRequest,
    db: AsyncSession = Depends(get_db),
):
    base_rate = await _get_current_rate(db)
    credit_premium = _credit_score_premium(body.credit_score)
    loan_type = body.loan_type if body.loan_type in VALID_LOAN_TYPES else "conventional"

    additional_savings = body.monthly_savings * body.wait_months
    future_down = body.down_payment + additional_savings
    future_savings = body.savings + additional_savings

    # Now — three rate scenarios
    now_flat = _build_scenario(
        body.annual_income, body.monthly_debt, body.credit_score,
        body.down_payment, body.savings, base_rate, credit_premium, loan_type, 0.0,
    )
    # Wait — three rate scenarios
    wait_flat = _build_scenario(
        body.annual_income, body.monthly_debt, body.credit_score,
        future_down, future_savings, base_rate, credit_premium, loan_type, 0.0,
    )
    wait_rate_down = _build_scenario(
        body.annual_income, body.monthly_debt, body.credit_score,
        future_down, future_savings, base_rate, credit_premium, loan_type, -0.005,
    )
    wait_rate_up = _build_scenario(
        body.annual_income, body.monthly_debt, body.credit_score,
        future_down, future_savings, base_rate, credit_premium, loan_type, +0.005,
    )

    price_delta = wait_flat["max_price"] - now_flat["max_price"]
    recommendation, factors = _make_recommendation(price_delta, base_rate * 100, body.monthly_savings)

    return {
        "now": now_flat,
        "wait": {
            "flat": wait_flat,
            "rate_down_half": wait_rate_down,
            "rate_up_half": wait_rate_up,
        },
        "additional_savings": round(additional_savings),
        "wait_months": body.wait_months,
        "price_delta_flat": price_delta,
        "recommendation": recommendation,
        "factors": factors,
        "current_rate_pct": round(base_rate * 100, 3),
    }

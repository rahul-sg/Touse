from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.macro_indicator import MacroIndicator


RATE_TIERS = {
    (760, 850): 0.000,
    (700, 759): 0.003,
    (680, 699): 0.005,
    (660, 679): 0.008,
    (640, 659): 0.015,
    (620, 639): 0.025,
}
DEFAULT_RATE = 0.068


def _credit_score_premium(score: int) -> float:
    for (low, high), premium in RATE_TIERS.items():
        if low <= score <= high:
            return premium
    return 0.04


def _monthly_payment(principal: float, annual_rate: float, years: int = 30) -> float:
    r = annual_rate / 12
    n = years * 12
    if r == 0:
        return principal / n
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)


def _max_loan_from_payment(monthly_payment: float, annual_rate: float, years: int = 30) -> float:
    r = annual_rate / 12
    n = years * 12
    if r == 0:
        return monthly_payment * n
    return monthly_payment * ((1 + r) ** n - 1) / (r * (1 + r) ** n)


async def _get_current_rate(db: AsyncSession) -> float:
    result = await db.execute(
        select(MacroIndicator.value)
        .where(MacroIndicator.series_name == "mortgage_rate_30y")
        .where(MacroIndicator.geo_id == "US")
        .order_by(desc(MacroIndicator.date))
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return DEFAULT_RATE
    return float(row) / 100  # FRED stores as percentage (e.g. 6.8)


async def calculate_affordability(body, db: AsyncSession) -> dict:
    base_rate = await _get_current_rate(db)
    rate = base_rate + _credit_score_premium(body.credit_score)

    gross_monthly = body.annual_income / 12
    max_housing_payment = gross_monthly * 0.28
    max_total_debt_payment = gross_monthly * 0.36
    available_for_housing = min(
        max_housing_payment,
        max_total_debt_payment - body.monthly_debt,
    )

    max_loan = _max_loan_from_payment(available_for_housing, rate)
    max_price = max_loan + body.down_payment
    payment_at_max = _monthly_payment(max_loan, rate)

    rate_shift = 0.005
    max_loan_if_rate_up = _max_loan_from_payment(available_for_housing, rate + rate_shift)
    buying_power_delta = (max_loan_if_rate_up + body.down_payment) - max_price

    return {
        "max_price": round(max_price),
        "max_loan": round(max_loan),
        "monthly_payment": round(payment_at_max),
        "rate_used": round(rate * 100, 3),
        "down_payment": body.down_payment,
        "buying_power_change_per_half_point": round(buying_power_delta),
    }

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.macro_indicator import MacroIndicator
from app.services.loan_calculators import LOAN_CALCULATORS, calc_conventional


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
    return float(row) / 100


async def calculate_affordability(body, db: AsyncSession) -> dict:
    base_rate = await _get_current_rate(db)
    credit_premium = _credit_score_premium(body.credit_score)

    loan_type = getattr(body, "loan_type", "conventional") or "conventional"
    calculator = LOAN_CALCULATORS.get(loan_type, calc_conventional)

    return calculator(body, base_rate, credit_premium)

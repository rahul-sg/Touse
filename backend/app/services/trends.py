from datetime import date
from dateutil.relativedelta import relativedelta
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.price_history import MetroPriceHistory


async def _price_n_months_ago(metro_id: str, months: int, db: AsyncSession) -> float | None:
    target = date.today() - relativedelta(months=months)
    # Get the closest available reading at or before that date
    result = await db.execute(
        select(MetroPriceHistory.median_price)
        .where(MetroPriceHistory.metro_id == metro_id)
        .where(MetroPriceHistory.date <= target)
        .order_by(MetroPriceHistory.date.desc())
        .limit(1)
    )
    val = result.scalar_one_or_none()
    return float(val) if val is not None else None


async def _latest_price(metro_id: str, db: AsyncSession) -> float | None:
    result = await db.execute(
        select(MetroPriceHistory.median_price)
        .where(MetroPriceHistory.metro_id == metro_id)
        .order_by(MetroPriceHistory.date.desc())
        .limit(1)
    )
    val = result.scalar_one_or_none()
    return float(val) if val is not None else None


def _pct_change(current: float | None, prior: float | None) -> float | None:
    if current is None or prior is None or prior == 0:
        return None
    return round((current - prior) / prior * 100, 2)


async def get_trends(metro_id: str, db: AsyncSession) -> dict:
    current = await _latest_price(metro_id, db)
    price_3m_ago = await _price_n_months_ago(metro_id, 3, db)
    price_12m_ago = await _price_n_months_ago(metro_id, 12, db)

    return {
        "current_median_price": current,
        "trend_3m": _pct_change(current, price_3m_ago),
        "trend_12m": _pct_change(current, price_12m_ago),
    }

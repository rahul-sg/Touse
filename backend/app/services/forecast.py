from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.forecast_result import ForecastResult
from app.services.trends import get_trends

# Prefer LightGBM (richer features) over Prophet when both exist
MODEL_PREFERENCE = ["lightgbm_v1", "prophet_v1"]


async def get_metro_forecast(metro_id: str, db: AsyncSession) -> dict:
    # Try each model version in preference order
    cached = None
    for version in MODEL_PREFERENCE:
        result = await db.execute(
            select(ForecastResult)
            .where(ForecastResult.metro_id == metro_id)
            .where(ForecastResult.model_version == version)
            .order_by(desc(ForecastResult.trained_at))
            .limit(1)
        )
        row = result.scalar_one_or_none()
        if row:
            cached = row
            break

    # Always compute live trends from raw price history
    trends = await get_trends(metro_id, db)

    if cached:
        return {
            "metro_id": metro_id,
            "model_version": cached.model_version,
            "trained_at": cached.trained_at.isoformat(),
            "current_median_price": trends["current_median_price"],
            "trend_3m": cached.trend_3m,
            "trend_12m": cached.trend_12m,
            "forecast_12m": cached.forecast_12m or [],
            "top_drivers": cached.top_drivers or {},
        }

    # No model trained yet — return trend indicators only
    return {
        "metro_id": metro_id,
        "model_version": None,
        "trained_at": None,
        "current_median_price": trends["current_median_price"],
        "trend_3m": trends["trend_3m"],
        "trend_12m": trends["trend_12m"],
        "forecast_12m": [],
        "top_drivers": {},
        "note": "Forecast model not yet trained for this metro. Showing trend indicators only.",
    }

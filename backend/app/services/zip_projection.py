"""
ZIP-level price projection — Prophet forecast trained on zip_price_history.

This is the ZIP-native replacement for the (never-populated) metro forecast
pipeline. Forecasts are trained on demand the first time a ZIP is requested,
then cached in zip_forecast_results so subsequent requests are instant.
"""
import asyncio
import logging
from datetime import date, datetime

import pandas as pd
from prophet import Prophet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.zip_price_history import ZipPriceHistory
from app.models.zip_forecast_result import ZipForecastResult

# Prophet/Stan are chatty — keep their output out of the API logs.
logging.getLogger("prophet").setLevel(logging.WARNING)
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)

MODEL_VERSION = "prophet_zip_v1"
MIN_MONTHS = 24          # Prophet needs a couple of years to learn seasonality
FORECAST_MONTHS = 12
HISTORY_TAIL_MONTHS = 6  # actuals shown before the projection for chart context
MAX_AGE_DAYS = 30        # re-train a cached forecast once it is older than this


def _fit_and_forecast(
    history: list[tuple[date, float]],
) -> tuple[list[dict], float, float | None]:
    """Fit Prophet on monthly history and return (points, current_value, pct_12m).

    `points` is a chart-ready list of {month, price, lower, upper}: a short tail
    of actuals (zero-width band) followed by 12 projected months (widening band).
    This is CPU-bound and synchronous — call it via asyncio.to_thread.
    """
    df = pd.DataFrame(history, columns=["ds", "y"])
    df["ds"] = pd.to_datetime(df["ds"])
    df["y"] = df["y"].astype(float)

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.80,           # 80% confidence band
        changepoint_prior_scale=0.05,  # conservative — home values move slowly
    )
    model.fit(df)

    future = model.make_future_dataframe(periods=FORECAST_MONTHS, freq="MS")
    forecast = model.predict(future)

    last_actual = df["ds"].max()
    current_value = float(df.iloc[-1]["y"])

    points: list[dict] = []
    # Tail of actuals — band collapses to the real value.
    tail = df[df["ds"] > last_actual - pd.DateOffset(months=HISTORY_TAIL_MONTHS)]
    for _, row in tail.iterrows():
        v = round(float(row["y"]))
        points.append({"month": row["ds"].strftime("%Y-%m"), "price": v, "lower": v, "upper": v})

    # Projected months — widening confidence band.
    future_only = forecast[forecast["ds"] > last_actual]
    for _, row in future_only.iterrows():
        points.append({
            "month": row["ds"].strftime("%Y-%m"),
            "price": round(float(row["yhat"])),
            "lower": round(float(row["yhat_lower"])),
            "upper": round(float(row["yhat_upper"])),
        })

    pct_12m: float | None = None
    if current_value and not future_only.empty:
        final = float(future_only.iloc[-1]["yhat"])
        pct_12m = round((final - current_value) / current_value * 100, 2)

    return points, current_value, pct_12m


def _serialize(row: ZipForecastResult) -> dict:
    return {
        "zip_code": row.zip_code,
        "model_version": row.model_version,
        "trained_at": row.trained_at.isoformat(),
        "current_value": row.current_value,
        "forecast_12m_pct": row.forecast_12m_pct,
        "data_points": row.data_points,
        "forecast_12m": row.forecast_12m or [],
    }


async def get_or_train(zip_code: str, db: AsyncSession) -> dict | None:
    """Return a cached projection for the ZIP, training one on demand if needed.

    Returns None when the ZIP has too little price history to model.
    """
    cached = await db.scalar(
        select(ZipForecastResult).where(ZipForecastResult.zip_code == zip_code)
    )
    if cached and (datetime.utcnow() - cached.trained_at).days < MAX_AGE_DAYS:
        return _serialize(cached)

    rows = (
        await db.execute(
            select(ZipPriceHistory.date, ZipPriceHistory.median_value)
            .where(
                ZipPriceHistory.zip_code == zip_code,
                ZipPriceHistory.median_value.isnot(None),
            )
            .order_by(ZipPriceHistory.date)
        )
    ).all()
    history = [(d, float(v)) for d, v in rows]
    if len(history) < MIN_MONTHS:
        return None

    # Prophet fitting is CPU-bound — run it off the event loop.
    points, current_value, pct_12m = await asyncio.to_thread(_fit_and_forecast, history)

    if cached:
        cached.model_version = MODEL_VERSION
        cached.trained_at = datetime.utcnow()
        cached.current_value = current_value
        cached.forecast_12m_pct = pct_12m
        cached.data_points = len(history)
        cached.forecast_12m = points
        row = cached
    else:
        row = ZipForecastResult(
            zip_code=zip_code,
            model_version=MODEL_VERSION,
            trained_at=datetime.utcnow(),
            current_value=current_value,
            forecast_12m_pct=pct_12m,
            data_points=len(history),
            forecast_12m=points,
        )
        db.add(row)

    await db.commit()
    await db.refresh(row)
    return _serialize(row)

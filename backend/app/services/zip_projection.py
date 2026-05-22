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

MODEL_VERSION = "prophet_zip_v2"
MIN_MONTHS = 24          # Prophet needs a couple of years to learn seasonality
FORECAST_MONTHS = 12
HISTORY_TAIL_MONTHS = 6  # actuals shown before the projection for chart context
MAX_AGE_DAYS = 30        # re-train a cached forecast once it is older than this

# Long-run anchoring — blend the Prophet trend toward the ZIP's multi-year CAGR
# so a recent boom doesn't extrapolate at full slope for an entire year.
CAGR_WINDOW_YEARS = 10
CAGR_MIN, CAGR_MAX = -0.10, 0.12     # clamp the annual CAGR to a sane band
BLEND_NEAR, BLEND_FAR = 0.85, 0.40   # Prophet weight at month 1 vs month 12


def _long_run_monthly_cagr(df: pd.DataFrame, last_actual, current_value: float) -> float:
    """Compound monthly growth over the last CAGR_WINDOW_YEARS, clamped to a sane band."""
    window = df[df["ds"] >= last_actual - pd.DateOffset(years=CAGR_WINDOW_YEARS)]
    if len(window) < 24:
        return 0.0
    base_val = float(window.iloc[0]["y"])
    span_years = (last_actual - window.iloc[0]["ds"]).days / 365.25
    if base_val <= 0 or span_years <= 0:
        return 0.0
    annual = (current_value / base_val) ** (1 / span_years) - 1
    annual = max(CAGR_MIN, min(CAGR_MAX, annual))
    return (1 + annual) ** (1 / 12) - 1


def _fit_and_forecast(
    history: list[tuple[date, float]],
) -> tuple[list[dict], float, float | None]:
    """Fit Prophet on monthly history and return (points, current_value, pct_12m).

    `points` is a chart-ready list of {month, price, lower, upper}: a short tail
    of actuals (zero-width band) followed by 12 projected months (widening band).

    The raw Prophet trend extrapolates the most recent slope linearly, which
    over-projects after a boom. We blend each projected month toward the ZIP's
    long-run CAGR — trusting Prophet near-term, the historical norm further out.

    CPU-bound and synchronous — call it via asyncio.to_thread.
    """
    df = pd.DataFrame(history, columns=["ds", "y"])
    df["ds"] = pd.to_datetime(df["ds"])
    df["y"] = df["y"].astype(float)

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.80,           # 80% confidence band
        changepoint_prior_scale=0.03,  # low — home values move slowly
    )
    model.fit(df)

    future = model.make_future_dataframe(periods=FORECAST_MONTHS, freq="MS")
    forecast = model.predict(future)

    last_actual = df["ds"].max()
    current_value = float(df.iloc[-1]["y"])
    monthly_cagr = _long_run_monthly_cagr(df, last_actual, current_value)

    points: list[dict] = []
    # Tail of actuals — band collapses to the real value.
    tail = df[df["ds"] > last_actual - pd.DateOffset(months=HISTORY_TAIL_MONTHS)]
    for _, row in tail.iterrows():
        v = round(float(row["y"]))
        points.append({"month": row["ds"].strftime("%Y-%m"), "price": v, "lower": v, "upper": v})

    # Projected months — Prophet blended toward the long-run CAGR path.
    future_only = forecast[forecast["ds"] > last_actual].reset_index(drop=True)
    last_blended = current_value
    for i, row in future_only.iterrows():
        t = i + 1  # months ahead (1..FORECAST_MONTHS)
        prophet_yhat = float(row["yhat"])
        cagr_value = current_value * (1 + monthly_cagr) ** t
        if FORECAST_MONTHS > 1:
            weight = BLEND_NEAR - (BLEND_NEAR - BLEND_FAR) * (t - 1) / (FORECAST_MONTHS - 1)
        else:
            weight = BLEND_NEAR
        blended = weight * prophet_yhat + (1 - weight) * cagr_value
        delta = blended - prophet_yhat  # shift the band to recenter on the blend
        last_blended = blended
        points.append({
            "month": row["ds"].strftime("%Y-%m"),
            "price": round(blended),
            "lower": round(float(row["yhat_lower"]) + delta),
            "upper": round(float(row["yhat_upper"]) + delta),
        })

    pct_12m: float | None = None
    if current_value:
        pct_12m = round((last_blended - current_value) / current_value * 100, 2)

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
    # Reuse the cache only if it's fresh AND from the current model version.
    if (
        cached
        and cached.model_version == MODEL_VERSION
        and (datetime.utcnow() - cached.trained_at).days < MAX_AGE_DAYS
    ):
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

"""
ZIP-level price projection.

Per-ZIP Prophet still produces the monthly trajectory and confidence band, but
the 12-month endpoint is anchored to the global LightGBM panel model (read
from zip_lgbm_predictions, written periodically by the train_global_lgbm task).
If no LGBM prediction exists yet for a ZIP, the projection falls back to the
older long-run-CAGR blend — graceful degradation, no service interruption.

Forecasts are cached in zip_forecast_results so repeat requests are instant.
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
from app.models.zip_lgbm_prediction import ZipLgbmPrediction
from app.models.forecast_realization import ForecastRealization

# Prophet/Stan are chatty — keep their output out of the API logs.
logging.getLogger("prophet").setLevel(logging.WARNING)
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)

MODEL_VERSION = "prophet_zip_v6_typed"
MIN_MONTHS = 24          # Prophet needs a couple of years to learn seasonality
FORECAST_MONTHS = 12
HISTORY_TAIL_MONTHS = 6  # actuals shown before the projection for chart context
MAX_AGE_DAYS = 30        # re-train a cached forecast once it is older than this

# Long-run anchoring — blend the Prophet trend toward the ZIP's multi-year CAGR
# so a recent boom doesn't extrapolate at full slope for an entire year.
CAGR_WINDOW_YEARS = 20
CAGR_MIN, CAGR_MAX = -0.10, 0.06     # clamp the annual CAGR to a sane band
BLEND_NEAR, BLEND_FAR = 0.30, 0.15   # Prophet weight at month 1 vs month 12
# Heavy anchor weight throughout — Prophet provides shape + bands; the anchor
# (LGBM endpoint, or long-run CAGR for cold-start ZIPs) drives the level so
# the trajectory transitions smoothly from current_value to the endpoint.


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
    blend_anchor_price: float | None = None,
) -> tuple[list[dict], float, float | None]:
    """Fit Prophet on monthly history and return (points, current_value, pct_12m).

    `points` is a chart-ready list of {month, price, lower, upper}: a short tail
    of actuals (zero-width band) followed by 12 projected months (widening band).

    The raw Prophet trend extrapolates the most recent slope linearly, which
    over-predicts after a boom. We blend each projected month toward an anchor
    path — trusting Prophet near-term, the anchor further out:

      - If `blend_anchor_price` is given (the global LightGBM model's 12-month
        endpoint prediction), we anchor toward it. This is the production path:
        backtest-validated, removes Prophet's systematic over-prediction bias.

      - Otherwise we fall back to the ZIP's long-run CAGR — graceful behavior
        for cold-start ZIPs the global model hasn't predicted for yet.

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

    # Pick the anchor monthly growth rate: LGBM-implied if available, else CAGR.
    if blend_anchor_price and current_value > 0:
        monthly_growth = (blend_anchor_price / current_value) ** (1 / FORECAST_MONTHS) - 1
    else:
        monthly_growth = _long_run_monthly_cagr(df, last_actual, current_value)

    # Prophet's in-sample fit at the last actual month — used to rescale Prophet's
    # trajectory so it starts from current_value (otherwise the in-sample/out-of-sample
    # mismatch causes a visible jump in the first forecast month).
    prophet_at_anchor = forecast.loc[forecast["ds"] == last_actual, "yhat"]
    prophet_at_anchor = float(prophet_at_anchor.iloc[-1]) if not prophet_at_anchor.empty else current_value

    points: list[dict] = []
    # Tail of actuals — band collapses to the real value.
    tail = df[df["ds"] > last_actual - pd.DateOffset(months=HISTORY_TAIL_MONTHS)]
    for _, row in tail.iterrows():
        v = round(float(row["y"]))
        points.append({"month": row["ds"].strftime("%Y-%m"), "price": v, "lower": v, "upper": v})

    # Projected months — Prophet (rescaled to start from current_value) blended
    # toward the anchor path.
    future_only = forecast[forecast["ds"] > last_actual].reset_index(drop=True)
    last_blended = current_value
    for i, row in future_only.iterrows():
        t = i + 1  # months ahead (1..FORECAST_MONTHS)
        prophet_yhat = float(row["yhat"])
        # Rescale: keep Prophet's relative shape, anchor its level to current_value.
        prophet_scaled = current_value * (prophet_yhat / prophet_at_anchor) if prophet_at_anchor else prophet_yhat
        anchor_value = current_value * (1 + monthly_growth) ** t
        if FORECAST_MONTHS > 1:
            weight = BLEND_NEAR - (BLEND_NEAR - BLEND_FAR) * (t - 1) / (FORECAST_MONTHS - 1)
        else:
            weight = BLEND_NEAR
        blended = weight * prophet_scaled + (1 - weight) * anchor_value
        # Preserve Prophet's band width (in % terms), recenter it on the blended value.
        if prophet_yhat:
            rel_lower = float(row["yhat_lower"]) / prophet_yhat
            rel_upper = float(row["yhat_upper"]) / prophet_yhat
        else:
            rel_lower = rel_upper = 1.0
        last_blended = blended
        points.append({
            "month": row["ds"].strftime("%Y-%m"),
            "price": round(blended),
            "lower": round(blended * rel_lower),
            "upper": round(blended * rel_upper),
        })

    pct_12m: float | None = None
    if current_value:
        pct_12m = round((last_blended - current_value) / current_value * 100, 2)

    return points, current_value, pct_12m


VALID_HOME_TYPES = ("all", "single_family", "condo")


def _serialize(row: ZipForecastResult) -> dict:
    return {
        "zip_code": row.zip_code,
        "home_type": row.home_type,
        "model_version": row.model_version,
        "trained_at": row.trained_at.isoformat(),
        "current_value": row.current_value,
        "forecast_12m_pct": row.forecast_12m_pct,
        "data_points": row.data_points,
        "forecast_12m": row.forecast_12m or [],
    }


async def get_or_train(zip_code: str, db: AsyncSession, home_type: str = "all") -> dict | None:
    """Return a cached projection for the (ZIP, home_type), training on demand.

    Returns None when there's too little price history for that home type to model.
    """
    if home_type not in VALID_HOME_TYPES:
        home_type = "all"

    cached = await db.scalar(
        select(ZipForecastResult).where(
            ZipForecastResult.zip_code == zip_code,
            ZipForecastResult.home_type == home_type,
        )
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
                ZipPriceHistory.home_type == home_type,
                ZipPriceHistory.median_value.isnot(None),
            )
            .order_by(ZipPriceHistory.date)
        )
    ).all()
    history = [(d, float(v)) for d, v in rows]
    if len(history) < MIN_MONTHS:
        return None

    # If the global LightGBM model has a prediction for this (ZIP, home_type),
    # use its 12-month endpoint as the blend anchor. Otherwise fall back to the
    # long-run-CAGR anchor inside _fit_and_forecast.
    lgbm = await db.scalar(
        select(ZipLgbmPrediction).where(
            ZipLgbmPrediction.zip_code == zip_code,
            ZipLgbmPrediction.home_type == home_type,
        )
    )
    anchor_price = float(lgbm.predicted_endpoint_price) if lgbm else None

    # Prophet fitting is CPU-bound — run it off the event loop.
    points, current_value, pct_12m = await asyncio.to_thread(
        _fit_and_forecast, history, anchor_price
    )

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
            home_type=home_type,
            model_version=MODEL_VERSION,
            trained_at=datetime.utcnow(),
            current_value=current_value,
            forecast_12m_pct=pct_12m,
            data_points=len(history),
            forecast_12m=points,
        )
        db.add(row)

    # Record this freshly-trained projection in forecast_realizations so we can
    # measure its accuracy when the horizon arrives. We only insert when we
    # *trained* (not on cache hits), so the audit table reflects the model
    # versions that actually produced forecasts rather than every cache read.
    last_point = points[-1] if points else None
    if last_point and current_value:
        try:
            horizon_end = date.fromisoformat(last_point["month"] + "-01")
        except ValueError:
            horizon_end = None
        if horizon_end:
            db.add(
                ForecastRealization(
                    zip_code=zip_code,
                    home_type=home_type,
                    model_version=MODEL_VERSION,
                    served_at=datetime.utcnow(),
                    horizon_end=horizon_end,
                    current_price_at_serve=float(current_value),
                    predicted_endpoint_price=float(last_point["price"]),
                )
            )

    await db.commit()
    await db.refresh(row)
    return _serialize(row)

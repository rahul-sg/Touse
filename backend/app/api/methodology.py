"""Methodology / model-transparency endpoint.

Public: returns a snapshot of the most recent global LightGBM training run so
the Methodology page can show users exactly which model is serving their
forecast and how it performed on held-out data.
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.limiter import limiter
from app.models.model_run import ModelRun
from app.models.zip_lgbm_prediction import ZipLgbmPrediction
from app.models.zip_price_history import ZipPriceHistory


router = APIRouter(prefix="/api/v1/methodology", tags=["methodology"])


@router.get("/summary")
@limiter.limit("60/minute")
async def methodology_summary(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Snapshot of the model currently serving forecasts.

    Returns the most recent training run plus a few live coverage stats so
    users can see — at a glance — what's behind every forecast and how recently
    it was refreshed.
    """
    latest_run = (
        await db.execute(
            select(ModelRun).order_by(desc(ModelRun.trained_at)).limit(1)
        )
    ).scalar_one_or_none()

    # Coverage: how many (ZIP, home_type) combinations the served model
    # actually has predictions for. Useful for explaining gaps in condo/SFR.
    coverage_rows = (
        await db.execute(
            select(ZipLgbmPrediction.home_type, func.count())
            .group_by(ZipLgbmPrediction.home_type)
        )
    ).all()
    coverage = {ht: int(n) for ht, n in coverage_rows}

    latest_data_month = await db.scalar(select(func.max(ZipPriceHistory.date)))

    return {
        "model": (
            {
                "version": latest_run.model_version,
                "trained_at": latest_run.trained_at.isoformat(),
                "panel_rows": int(latest_run.panel_rows),
                "train_rows": int(latest_run.train_rows),
                "feature_count": int(latest_run.feature_count),
                "zips_predicted": int(latest_run.zips_predicted),
                "train_seconds": float(latest_run.train_seconds),
                "backtest_mape_all": (
                    float(latest_run.backtest_mape_all)
                    if latest_run.backtest_mape_all is not None else None
                ),
                "backtest_bias_all": (
                    float(latest_run.backtest_bias_all)
                    if latest_run.backtest_bias_all is not None else None
                ),
                "backtest_per_type": latest_run.backtest_per_type,
                "notes": latest_run.notes,
            }
            if latest_run else None
        ),
        "coverage": {
            "by_home_type": coverage,
            "total_predictions": sum(coverage.values()),
            "latest_price_month": (
                latest_data_month.isoformat() if latest_data_month else None
            ),
        },
        "features": [
            {"group": "Local price history",
             "items": ["lagged prices (1/3/6/12/24m)", "growth rates (1/3/6/12m)",
                       "rolling-average momentum (3m, 12m)"]},
            {"group": "US macro",
             "items": ["30-yr mortgage rate (+ 3m / 12m lags + 3m change)",
                       "CPI year-over-year",
                       "fed funds rate (+ 3m / 12m change)",
                       "unemployment", "housing starts",
                       "UMich consumer sentiment", "new-home sales"]},
            {"group": "Metro supply & rent (Zillow Research)",
             "items": ["for-sale inventory", "new listings",
                       "mean days-on-market (pending)", "% with price cut",
                       "median list price", "median rent", "rent-to-price ratio"]},
            {"group": "Cycle & seasonality",
             "items": ["election-year flag", "month sin/cos (yearly cycle)"]},
            {"group": "Identity",
             "items": ["ZIP code (categorical)", "home type (categorical: all / SFR / condo)"]},
        ],
        "pipeline": {
            "stage_1": "Global LightGBM panel predicts 12-month endpoint per (zip, home_type) — retrained monthly on every Zillow ZHVI release.",
            "stage_2": "Per-(zip, home_type) Prophet model shapes the monthly path, with its endpoint blended toward the LightGBM anchor.",
            "fallback": "ZIPs the LightGBM panel hasn't predicted for (insufficient history) gracefully fall back to a 20-year CAGR anchor.",
        },
    }

"""
Celery tasks for the ZIP forecasting pipeline.

  train_global_lgbm     — fits the global LightGBM panel model and writes a
                          12-month endpoint prediction for every ZIP. Runs
                          monthly, after fresh Zillow data lands.

  refresh_zip_forecasts — re-fits the per-ZIP Prophet trajectory for the
                          stalest cached forecasts, using the latest LGBM
                          endpoint as the blend anchor. Runs monthly, after
                          train_global_lgbm.

  realize_forecasts     — fills in actual_price + abs_pct_error for served
                          forecasts whose 12-month horizon has arrived.
                          Powers the per-ZIP track record on the forecast
                          page. Cheap, idempotent — safe to run frequently.
"""
import os
from datetime import datetime

from tasks.celery_app import app

_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://touse:touse@localhost:5432/touse",
).replace("postgresql+asyncpg://", "postgresql+psycopg2://")

# Cap per run — each Prophet fit takes ~1-2s, so retraining every cached ZIP
# would run for hours once the cache holds thousands. The stalest are picked
# first; the rest get retrained on their next on-demand request (or next run).
MAX_REFRESH_PER_RUN = 500


@app.task(name="tasks.ml_tasks.train_global_lgbm", bind=True, max_retries=1)
def train_global_lgbm(self):
    """Fit the global LightGBM panel model and persist per-ZIP predictions."""
    try:
        from app.ml.train_lgbm import train_and_save_predictions
        n = train_and_save_predictions()
        print(f"train_global_lgbm: wrote {n} predictions")
    except Exception as exc:
        # Big job; retry once after an hour rather than hammering.
        raise self.retry(exc=exc, countdown=60 * 60)


@app.task(name="tasks.ml_tasks.refresh_zip_forecasts", bind=True, max_retries=2)
def refresh_zip_forecasts(self):
    """Re-train the Prophet trajectory for the stalest cached ZIPs (capped per run),
    anchored to the latest LGBM 12-month endpoint."""
    try:
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session

        from app.models.zip_forecast_result import ZipForecastResult
        from app.models.zip_lgbm_prediction import ZipLgbmPrediction
        from app.models.zip_price_history import ZipPriceHistory
        from app.services.zip_projection import _fit_and_forecast, MODEL_VERSION, MIN_MONTHS

        engine = create_engine(_DB_URL)
        refreshed = 0
        with Session(engine) as session:
            zip_codes = session.execute(
                select(ZipForecastResult.zip_code)
                .order_by(ZipForecastResult.trained_at.asc())
                .limit(MAX_REFRESH_PER_RUN)
            ).scalars().all()

            for zip_code in zip_codes:
                rows = session.execute(
                    select(ZipPriceHistory.date, ZipPriceHistory.median_value)
                    .where(
                        ZipPriceHistory.zip_code == zip_code,
                        ZipPriceHistory.median_value.isnot(None),
                    )
                    .order_by(ZipPriceHistory.date)
                ).all()
                history = [(d, float(v)) for d, v in rows]
                if len(history) < MIN_MONTHS:
                    continue

                lgbm = session.execute(
                    select(ZipLgbmPrediction).where(ZipLgbmPrediction.zip_code == zip_code)
                ).scalar_one_or_none()
                anchor_price = float(lgbm.predicted_endpoint_price) if lgbm else None

                points, current_value, pct = _fit_and_forecast(history, anchor_price)
                row = session.execute(
                    select(ZipForecastResult).where(ZipForecastResult.zip_code == zip_code)
                ).scalar_one()
                row.model_version = MODEL_VERSION
                row.trained_at = datetime.utcnow()
                row.current_value = current_value
                row.forecast_12m_pct = pct
                row.data_points = len(history)
                row.forecast_12m = points
                refreshed += 1

            session.commit()
        print(f"refresh_zip_forecasts: refreshed {refreshed}/{len(zip_codes)} ZIPs")
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * 30)


@app.task(name="tasks.ml_tasks.realize_forecasts", bind=True, max_retries=2)
def realize_forecasts(self):
    """Fill actual_price + error metrics for served forecasts whose horizon arrived.

    Scans forecast_realizations for rows with `actual_price IS NULL` and
    `horizon_end <= today`. For each, looks up the matching `(zip, home_type,
    horizon_end)` row in zip_price_history and writes the realized price plus
    the absolute and signed % error vs the predicted endpoint.

    Idempotent: rows with `actual_price IS NOT NULL` are skipped, so re-runs
    are no-ops. Designed to be cheap enough to schedule daily.
    """
    try:
        from datetime import date as _date, datetime
        from sqlalchemy import create_engine, select, and_
        from sqlalchemy.orm import Session

        from app.models.forecast_realization import ForecastRealization
        from app.models.zip_price_history import ZipPriceHistory

        engine = create_engine(_DB_URL)
        filled = 0
        skipped_missing = 0

        with Session(engine) as session:
            pending = session.execute(
                select(ForecastRealization).where(
                    and_(
                        ForecastRealization.actual_price.is_(None),
                        ForecastRealization.horizon_end <= _date.today(),
                    )
                )
            ).scalars().all()

            for row in pending:
                actual = session.execute(
                    select(ZipPriceHistory.median_value).where(
                        ZipPriceHistory.zip_code == row.zip_code,
                        ZipPriceHistory.home_type == row.home_type,
                        ZipPriceHistory.date == row.horizon_end,
                    )
                ).scalar_one_or_none()
                if actual is None or actual == 0:
                    skipped_missing += 1
                    continue

                actual = float(actual)
                row.actual_price = actual
                row.abs_pct_error = abs(row.predicted_endpoint_price - actual) / actual
                row.signed_pct_error = (row.predicted_endpoint_price - actual) / actual
                row.realized_at = datetime.utcnow()
                filled += 1

            session.commit()

        print(
            f"realize_forecasts: filled {filled}, "
            f"still missing actual {skipped_missing}, "
            f"total pending {len(pending)}"
        )
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * 60)

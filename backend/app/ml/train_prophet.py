"""
Prophet-based price forecast trainer.

For each metro with sufficient history (>=24 months), trains a Prophet model
and writes a 12-month forecast with 80% confidence intervals to forecast_results.

Run directly:
    python3 -m app.ml.train_prophet --metro-id "austin-round_rock-georgetown,_tx"
    python3 -m app.ml.train_prophet --all

Or triggered monthly by Celery task.
"""
import argparse
import sys
import os
from datetime import datetime, date

import pandas as pd
from prophet import Prophet
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.models.price_history import MetroPriceHistory
from app.models.forecast_result import ForecastResult
from app.models.region import Region

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://touse:touse@localhost:5432/touse",
).replace("postgresql+asyncpg://", "postgresql+psycopg2://")

MODEL_VERSION = "prophet_v1"
MIN_MONTHS = 24
FORECAST_MONTHS = 12


def load_price_history(session: Session, metro_id: str) -> pd.DataFrame:
    rows = session.execute(
        select(MetroPriceHistory.date, MetroPriceHistory.median_price)
        .where(MetroPriceHistory.metro_id == metro_id)
        .order_by(MetroPriceHistory.date)
    ).all()
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows, columns=["ds", "y"])
    df["ds"] = pd.to_datetime(df["ds"])
    df["y"] = df["y"].astype(float)
    return df


def train_and_forecast(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Returns (forecast_df, top_drivers).
    forecast_df has columns: ds, yhat, yhat_lower, yhat_upper (12 future rows).
    """
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=False,
        daily_seasonality=False,
        interval_width=0.80,
        changepoint_prior_scale=0.05,  # conservative — housing prices are slow-moving
    )
    model.fit(df)

    future = model.make_future_dataframe(periods=FORECAST_MONTHS, freq="MS")
    forecast = model.predict(future)

    future_only = forecast[forecast["ds"] > df["ds"].max()][
        ["ds", "yhat", "yhat_lower", "yhat_upper"]
    ].copy()

    # Top drivers from changepoint magnitudes
    deltas = model.params["delta"].mean(axis=0)
    changepoints = model.changepoints
    top_up = changepoints[deltas.argsort()[-3:][::-1]].dt.strftime("%Y-%m").tolist()
    top_down = changepoints[deltas.argsort()[:3]].dt.strftime("%Y-%m").tolist()

    top_drivers = {
        "strongest_growth_periods": top_up,
        "strongest_decline_periods": top_down,
    }

    return future_only, top_drivers


def compute_trends(df: pd.DataFrame) -> tuple[float | None, float | None]:
    if df.empty:
        return None, None
    latest = float(df.iloc[-1]["y"])

    def _n_months_ago(n: int) -> float | None:
        cutoff = df["ds"].max() - pd.DateOffset(months=n)
        prior = df[df["ds"] <= cutoff]
        return float(prior.iloc[-1]["y"]) if not prior.empty else None

    p3 = _n_months_ago(3)
    p12 = _n_months_ago(12)

    trend_3m = round((latest - p3) / p3 * 100, 2) if p3 else None
    trend_12m = round((latest - p12) / p12 * 100, 2) if p12 else None
    return trend_3m, trend_12m


def save_forecast(
    session: Session,
    metro_id: str,
    trend_3m: float | None,
    trend_12m: float | None,
    future_df: pd.DataFrame,
    top_drivers: dict,
) -> None:
    forecast_12m = [
        {
            "month": row["ds"].strftime("%Y-%m"),
            "price": round(float(row["yhat"])),
            "lower": round(float(row["yhat_lower"])),
            "upper": round(float(row["yhat_upper"])),
        }
        for _, row in future_df.iterrows()
    ]

    stmt = insert(ForecastResult).values(
        metro_id=metro_id,
        model_version=MODEL_VERSION,
        trained_at=datetime.utcnow(),
        trend_3m=trend_3m,
        trend_12m=trend_12m,
        forecast_12m=forecast_12m,
        top_drivers=top_drivers,
    ).on_conflict_do_update(
        constraint="uq_metro_model",
        set_={
            "trained_at": datetime.utcnow(),
            "trend_3m": trend_3m,
            "trend_12m": trend_12m,
            "forecast_12m": forecast_12m,
            "top_drivers": top_drivers,
        },
    )
    session.execute(stmt)
    session.commit()


def train_metro(session: Session, metro_id: str) -> bool:
    df = load_price_history(session, metro_id)
    if len(df) < MIN_MONTHS:
        print(f"  Skipping {metro_id} — only {len(df)} months of data (need {MIN_MONTHS})")
        return False

    print(f"  Training Prophet on {len(df)} months of data...")
    future_df, top_drivers = train_and_forecast(df)
    trend_3m, trend_12m = compute_trends(df)
    save_forecast(session, metro_id, trend_3m, trend_12m, future_df, top_drivers)
    print(f"  Saved forecast for {metro_id} (trend_12m={trend_12m}%)")
    return True


def train_all(session: Session) -> None:
    metro_ids = session.execute(
        select(Region.metro_id)
    ).scalars().all()

    total = len(metro_ids)
    trained = 0
    for i, metro_id in enumerate(metro_ids, 1):
        print(f"[{i}/{total}] {metro_id}")
        if train_metro(session, metro_id):
            trained += 1

    print(f"\nDone. Trained {trained}/{total} metros.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--metro-id", type=str)
    group.add_argument("--all", action="store_true")
    args = parser.parse_args()

    engine = create_engine(DATABASE_URL)
    with Session(engine) as session:
        if args.all:
            train_all(session)
        else:
            train_metro(session, args.metro_id)

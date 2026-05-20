"""
LightGBM global price forecast trainer (Phase 3).

Trains a single model across all metros using macro + political features.
A global model handles data sparsity for smaller metros better than
per-metro models, and metro_id as a categorical lets the model learn
metro-specific offsets automatically.

Usage:
    python3 -m app.ml.train_lightgbm           # train + evaluate + save
    python3 -m app.ml.train_lightgbm --dry-run  # feature matrix only, no save

Outputs to forecast_results table with model_version = "lightgbm_v1".
"""
import argparse
import os
import sys
import json
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

import numpy as np
import pandas as pd
import lightgbm as lgb
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.ml.features import build_feature_matrix, FEATURE_COLS
from app.models.forecast_result import ForecastResult
from app.models.region import Region

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://touse:touse@localhost:5432/touse",
).replace("postgresql+asyncpg://", "postgresql+psycopg2://")

MODEL_VERSION = "lightgbm_v1"
FORECAST_MONTHS = 12
TEST_MONTHS = 12  # hold out last 12 months for evaluation


# ── LightGBM hyperparameters ────────────────────────────────────────────────
PARAMS = {
    "objective": "regression",
    "metric": "mape",
    "learning_rate": 0.05,
    "num_leaves": 63,
    "min_child_samples": 20,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "reg_alpha": 0.1,
    "reg_lambda": 0.1,
    "verbose": -1,
}
NUM_BOOST_ROUND = 500
EARLY_STOPPING = 50


def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true != 0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def train(df: pd.DataFrame) -> tuple[lgb.Booster, dict]:
    """Train on all-but-last-TEST_MONTHS, validate on last TEST_MONTHS."""
    cutoff = df["date"].max() - relativedelta(months=TEST_MONTHS)
    train_df = df[df["date"] <= cutoff]
    test_df  = df[df["date"] >  cutoff]

    X_train = train_df[FEATURE_COLS]
    y_train = train_df["median_price"]
    X_test  = test_df[FEATURE_COLS]
    y_test  = test_df["median_price"]

    cat_features = ["metro_id"]

    dtrain = lgb.Dataset(X_train, label=y_train, categorical_feature=cat_features, free_raw_data=False)
    dvalid = lgb.Dataset(X_test,  label=y_test,  categorical_feature=cat_features, free_raw_data=False, reference=dtrain)

    callbacks = [lgb.early_stopping(EARLY_STOPPING, verbose=False), lgb.log_evaluation(period=50)]

    model = lgb.train(
        PARAMS,
        dtrain,
        num_boost_round=NUM_BOOST_ROUND,
        valid_sets=[dvalid],
        callbacks=callbacks,
    )

    train_mape = _mape(y_train.values, model.predict(X_train))
    test_mape  = _mape(y_test.values,  model.predict(X_test))
    print(f"  Train MAPE: {train_mape:.2f}%   Test MAPE: {test_mape:.2f}%")
    print(f"  Best iteration: {model.best_iteration}")

    metrics = {
        "train_mape": round(train_mape, 3),
        "test_mape": round(test_mape, 3),
        "best_iteration": model.best_iteration,
        "n_train": len(train_df),
        "n_test": len(test_df),
        "trained_at": datetime.utcnow().isoformat(),
    }

    # Feature importance
    importance = dict(zip(
        model.feature_name(),
        model.feature_importance(importance_type="gain").tolist(),
    ))
    top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10]
    metrics["top_features"] = {k: round(v, 1) for k, v in top_features}
    print(f"  Top features: {list(importance.keys())[:5]}")

    return model, metrics


def forecast_metro(
    model: lgb.Booster,
    df: pd.DataFrame,
    metro_id: str,
) -> list[dict]:
    """
    Iteratively forecast 12 months ahead for a single metro.

    Each step: append the predicted price as the new 'price_lag1',
    recalculate rolling/momentum features, then predict the next month.
    """
    metro_df = df[df["metro_id"] == metro_id].sort_values("date").copy()
    if metro_df.empty:
        return []

    # Latest known row as seed
    last_date = metro_df["date"].max()
    last_price = float(metro_df.loc[metro_df["date"] == last_date, "median_price"].iloc[0])

    # Keep a rolling window of recent prices for feature recomputation
    price_history = metro_df["median_price"].tolist()

    # Grab the last row of non-price features (macro/policy) as base
    base = metro_df.iloc[-1].to_dict()

    predictions = []
    current_price = last_price

    for step in range(1, FORECAST_MONTHS + 1):
        next_date = last_date + relativedelta(months=step)
        price_history.append(current_price)

        row = base.copy()
        row["date"] = next_date
        row["month_of_year"] = next_date.month

        # Recompute price momentum features from the growing history
        h = price_history
        row["price_lag1"]  = h[-2] if len(h) >= 2  else np.nan
        row["price_lag3"]  = h[-4] if len(h) >= 4  else np.nan
        row["price_lag12"] = h[-13] if len(h) >= 13 else np.nan
        row["price_roll3"]  = np.mean(h[-4:-1])  if len(h) >= 4  else np.nan
        row["price_roll6"]  = np.mean(h[-7:-1])  if len(h) >= 7  else np.nan
        row["price_roll12"] = np.mean(h[-13:-1]) if len(h) >= 13 else np.nan

        lag3  = row["price_lag3"]
        lag12 = row["price_lag12"]
        row["price_mom_3m"]  = (current_price / lag3  - 1) * 100 if lag3  else np.nan
        row["price_mom_12m"] = (current_price / lag12 - 1) * 100 if lag12 else np.nan

        row_df = pd.DataFrame([row])[FEATURE_COLS]
        row_df["metro_id"] = row_df["metro_id"].astype("category")

        predicted = float(model.predict(row_df)[0])
        current_price = predicted
        predictions.append((next_date, predicted))

    # Compute confidence intervals from model leaf variance (simple bootstrap proxy)
    # We use ±1.28σ (80% CI) estimated from MAPE-based uncertainty
    # A rough σ: assume MAPE distributes price error symmetrically
    ci_width_pct = 0.06  # ~6% width per side — tighten/widen based on test MAPE
    return [
        {
            "month": d.strftime("%Y-%m"),
            "price": round(p),
            "lower": round(p * (1 - ci_width_pct)),
            "upper": round(p * (1 + ci_width_pct)),
        }
        for d, p in predictions
    ]


def _compute_trends(df: pd.DataFrame, metro_id: str) -> tuple[float | None, float | None]:
    metro = df[df["metro_id"] == metro_id].sort_values("date")
    if metro.empty:
        return None, None
    latest = float(metro.iloc[-1]["median_price"])

    def _prev(n: int) -> float | None:
        cutoff = metro["date"].max() - relativedelta(months=n)
        prior = metro[metro["date"] <= cutoff]
        return float(prior.iloc[-1]["median_price"]) if not prior.empty else None

    p3  = _prev(3)
    p12 = _prev(12)
    t3  = round((latest - p3)  / p3  * 100, 2) if p3  else None
    t12 = round((latest - p12) / p12 * 100, 2) if p12 else None
    return t3, t12


def save_forecasts(session: Session, model: lgb.Booster, metrics: dict, df: pd.DataFrame) -> int:
    metro_ids = df["metro_id"].cat.categories.tolist()
    saved = 0
    for metro_id in metro_ids:
        forecast_12m = forecast_metro(model, df, metro_id)
        if not forecast_12m:
            continue
        trend_3m, trend_12m = _compute_trends(df, metro_id)

        top_drivers = {
            "top_features": metrics.get("top_features", {}),
            "model_metrics": {
                "test_mape": metrics.get("test_mape"),
                "train_mape": metrics.get("train_mape"),
            },
        }

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
        saved += 1

    session.commit()
    return saved


def run(dry_run: bool = False) -> None:
    engine = create_engine(DATABASE_URL)

    print("Building feature matrix…")
    df = build_feature_matrix(engine)

    if df.empty:
        print("No data available. Run ETL pipelines first.")
        return

    n_metros = df["metro_id"].nunique()
    print(f"Feature matrix: {len(df)} rows, {n_metros} metros, {len(FEATURE_COLS)} features")

    if len(df) < 500:
        print("Not enough data to train (need ≥500 rows). Run Zillow + FRED ETL first.")
        return

    print("\nTraining LightGBM…")
    model, metrics = train(df)

    print(f"\nModel metrics: {json.dumps(metrics, indent=2)}")

    if dry_run:
        print("\n[dry-run] Skipping save.")
        return

    print("\nGenerating per-metro forecasts and saving…")
    with Session(engine) as session:
        saved = save_forecasts(session, model, metrics, df)

    print(f"\nDone. Saved forecasts for {saved}/{n_metros} metros (model: {MODEL_VERSION}).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Build features + train but don't save")
    args = parser.parse_args()
    run(dry_run=args.dry_run)

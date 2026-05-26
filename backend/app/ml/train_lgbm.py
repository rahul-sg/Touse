"""
Global LightGBM panel model for 12-month ZIP price-growth forecasting.

A direct, honest comparison vs the current Prophet+CAGR-blend baseline:
the evaluation window and ZIP sample are matched to the Prophet backtest
(30 ZIPs by default, last 12 months of held-out cutoffs).

Features per (zip, month):
  - Lagged prices and growth rates (1, 3, 6, 12, 24 months)
  - 3 / 12-month rolling means of monthly growth
  - US macro at month: 30-yr mortgage rate (+ 3/12m lags + 3m change),
    CPI year-over-year, unemployment, fed funds, housing starts,
    UMich consumer sentiment, new-home sales
  - Cyclical month encoding (sin/cos)
  - ZIP code as a categorical

Target: 12-month price growth = price(t+12)/price(t) − 1.

CLI:
    python -m app.ml.train_lgbm                          # 30-ZIP eval (matches Prophet baseline)
    python -m app.ml.train_lgbm --sample 100 --seed 42
    python -m app.ml.train_lgbm --csv out.csv
"""
import argparse
import os
import random
import sys
import time
from datetime import datetime

import numpy as np
import pandas as pd
import lightgbm as lgb
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import insert as pg_insert

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.ml.backtest import DEFAULT_MIN_TRAIN, DEFAULT_FOLDS  # match Prophet baseline scope
from app.models.zip_lgbm_prediction import ZipLgbmPrediction
from app.models.model_run import ModelRun
from etl.zillow_metro import normalize_metro  # noqa: E402 — keep DB models above

MODEL_VERSION = "lgbm_panel_v4_typed"
VALID_HOME_TYPES = ("all", "single_family", "condo")

# Rows must have the target and the longest core price lag; everything else
# (macros, sentiment, supply) can be NaN — LightGBM treats missing as a signal.
REQUIRED_FOR_FIT = ["target", "price_lag_12m"]

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://touse:touse@localhost:5433/touse",
).replace("postgresql+asyncpg://", "postgresql+psycopg2://")

HORIZON_MONTHS = 12          # match what the user actually sees on the forecast page
EVAL_FOLDS = DEFAULT_FOLDS   # 12 — same as Prophet backtest
SAMPLE_DEFAULT = 30          # same sample size as Prophet baseline


# ── Feature engineering ───────────────────────────────────────────────────────

def _load_prices(engine) -> pd.DataFrame:
    """Recent monthly ZIP prices per (zip, home_type), sorted by (zip, home_type, date).

    Loads from 2017-01-01 onward — enough for 24-month lag features plus a
    12-month target horizon, while keeping the in-memory footprint manageable
    on a t3.small (avoids OOM on the full ~28-year dataset).

    Per-(zip,home_type) ordering matters — the lag features are computed within
    each (zip, home_type) group, so a condo's history must not leak into a SFR
    lag for the same ZIP.
    """
    df = pd.read_sql(
        "SELECT zip_code, home_type, date, median_value, metro "
        "FROM zip_price_history WHERE median_value IS NOT NULL AND date >= '2017-01-01'",
        engine,
    )
    df["date"] = pd.to_datetime(df["date"])
    df["metro_norm"] = df["metro"].fillna("").map(normalize_metro)
    return df.sort_values(["zip_code", "home_type", "date"]).reset_index(drop=True)


def _load_metro_supply(engine) -> pd.DataFrame:
    """Zillow metro supply + rent panel with within-metro YoY derivations."""
    df = pd.read_sql(
        "SELECT metro, date, invt_fs, new_listings, mean_doz_pending, "
        "perc_price_cut, median_list_price, median_rent FROM metro_supply_history",
        engine,
    )
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["metro", "date"])
    g = df.groupby("metro", sort=False)
    df["invt_fs_yoy"] = df["invt_fs"] / g["invt_fs"].shift(12) - 1
    df["new_listings_yoy"] = df["new_listings"] / g["new_listings"].shift(12) - 1
    df["rent_yoy"] = df["median_rent"] / g["median_rent"].shift(12) - 1
    return df.rename(columns={"metro": "metro_norm"})


def _load_macro(engine) -> pd.DataFrame:
    """US macro series, pivoted wide by series_name, resampled to month-end."""
    df = pd.read_sql(
        "SELECT date, series_name, value FROM macro_indicators WHERE geo_id = 'US'",
        engine,
    )
    df["date"] = pd.to_datetime(df["date"])
    wide = df.pivot_table(index="date", columns="series_name", values="value").sort_index()
    # mortgage_rate_30y is weekly; others monthly. Forward-fill to align cadences.
    wide = wide.resample("D").ffill().resample("ME").last()  # month-end
    wide = wide.ffill().reset_index().rename(columns={"date": "macro_date"})

    # CPI year-over-year (% change in the index)
    wide["cpi_yoy"] = wide["cpi"].pct_change(12) * 100
    # Mortgage rate lags + 3m change
    wide["mortgage_rate_lag_3m"] = wide["mortgage_rate_30y"].shift(3)
    wide["mortgage_rate_lag_12m"] = wide["mortgage_rate_30y"].shift(12)
    wide["mortgage_rate_change_3m"] = wide["mortgage_rate_30y"] - wide["mortgage_rate_lag_3m"]
    # Step E: Fed-funds level + deltas — captures monetary-regime shifts that
    # the absolute rate alone hides (a rising rate environment is different
    # from a stable one at the same level).
    wide["fed_funds_change_3m"] = wide["fed_funds_rate"] - wide["fed_funds_rate"].shift(3)
    wide["fed_funds_change_12m"] = wide["fed_funds_rate"] - wide["fed_funds_rate"].shift(12)
    return wide


def build_panel(engine) -> tuple[pd.DataFrame, list[str]]:
    """Build the full (zip, home_type, month) feature panel + feature column list."""
    prices = _load_prices(engine)
    # Lag/growth features computed WITHIN each (zip, home_type) — must not let
    # a condo's history leak into a SFR lag for the same ZIP.
    g = prices.groupby(["zip_code", "home_type"], sort=False)["median_value"]

    for lag in (1, 3, 6, 12, 24):
        prices[f"price_lag_{lag}m"] = g.shift(lag)
    for lag in (1, 3, 6, 12):
        prices[f"growth_{lag}m"] = prices["median_value"] / prices[f"price_lag_{lag}m"] - 1
    g1 = prices.groupby(["zip_code", "home_type"], sort=False)["growth_1m"]
    prices["growth_3m_avg"] = g1.transform(lambda s: s.rolling(3).mean())
    prices["growth_12m_avg"] = g1.transform(lambda s: s.rolling(12).mean())

    # Target — price 12 months ahead in the same (zip, home_type) series
    prices["price_future"] = g.shift(-HORIZON_MONTHS)
    prices["target"] = prices["price_future"] / prices["median_value"] - 1

    # Seasonality (cyclic)
    months = prices["date"].dt.month
    prices["month_sin"] = np.sin(2 * np.pi * months / 12)
    prices["month_cos"] = np.cos(2 * np.pi * months / 12)

    # Macro join — as-of, backward (use latest macro known at or before the price date)
    macro = _load_macro(engine)
    prices = pd.merge_asof(
        prices.sort_values("date"),
        macro.sort_values("macro_date"),
        left_on="date", right_on="macro_date",
        direction="backward",
    ).sort_values(["zip_code", "home_type", "date"]).reset_index(drop=True)

    # Metro supply join — same month, by normalized metro name. Same-month is
    # OK (not leakage): supply at month t and price-growth from t→t+12 are
    # contemporaneous → future as far as the target is concerned.
    supply = _load_metro_supply(engine)
    prices = prices.merge(supply, on=["metro_norm", "date"], how="left")

    # Step D: rent-to-price ratio — classic valuation signal. Annualized rent ÷ price.
    # High ratio = buying is cheap vs renting (supports prices); low ratio = stretched.
    prices["rent_to_price_ratio"] = (12 * prices["median_rent"]) / prices["median_value"]

    # Step E: election year flag — Presidential + midterm cycles.
    prices["is_election_year"] = (prices["date"].dt.year % 2 == 0).astype(int)

    feature_cols = [
        "price_lag_1m", "price_lag_3m", "price_lag_6m", "price_lag_12m", "price_lag_24m",
        "growth_1m", "growth_3m", "growth_6m", "growth_12m",
        "growth_3m_avg", "growth_12m_avg",
        "mortgage_rate_30y", "mortgage_rate_lag_3m", "mortgage_rate_lag_12m",
        "mortgage_rate_change_3m",
        "cpi_yoy", "unemployment", "fed_funds_rate",
        "fed_funds_change_3m", "fed_funds_change_12m",   # Step E
        "housing_starts", "consumer_sentiment", "new_home_sales",
        # Metro supply / demand (Zillow Research)
        "invt_fs", "new_listings", "mean_doz_pending", "perc_price_cut",
        "invt_fs_yoy", "new_listings_yoy",
        # Step D: rent
        "median_rent", "rent_yoy", "rent_to_price_ratio",
        # Step E: election cycle
        "is_election_year",
        "month_sin", "month_cos",
        "zip_code",   # categorical
        "home_type",  # categorical — lets the model learn SFR vs condo dynamics
    ]
    return prices, feature_cols


# ── Sampling — match Prophet baseline ─────────────────────────────────────────

def _pick_eval_zips(panel: pd.DataFrame, n: int, seed: int) -> list[str]:
    """Same protocol as the Prophet backtest: ZIPs with enough history.

    Uses the 'all' home_type so the metric is apples-to-apples with prior
    backtests (Prophet baseline operated on the combined index).
    """
    need = DEFAULT_MIN_TRAIN + HORIZON_MONTHS + EVAL_FOLDS
    all_only = panel[panel["home_type"] == "all"]
    counts = all_only.groupby("zip_code").size()
    eligible = counts[counts >= need].index.tolist()
    random.seed(seed)
    return random.sample(eligible, min(n, len(eligible)))


# ── Train + evaluate ──────────────────────────────────────────────────────────

def build_and_train() -> tuple[lgb.LGBMRegressor, pd.DataFrame, list[str], pd.Timestamp, pd.Timestamp]:
    """Build the feature panel and train the global model. Returns
    (model, panel, feature_cols, earliest_cutoff, latest_cutoff).
    """
    engine = create_engine(DATABASE_URL)

    print("Loading prices + macro and building features...")
    t0 = time.time()
    panel, feature_cols = build_panel(engine)
    print(f"  panel: {len(panel):,} rows in {time.time()-t0:.1f}s")

    # Eval window matches the Prophet backtest: last EVAL_FOLDS months that
    # have a known 12-month-ahead target.
    max_date = panel["date"].max()
    latest_cutoff = max_date - pd.DateOffset(months=HORIZON_MONTHS)
    earliest_cutoff = latest_cutoff - pd.DateOffset(months=EVAL_FOLDS - 1)
    print(f"  eval cutoffs: {earliest_cutoff.date()} .. {latest_cutoff.date()}  ({EVAL_FOLDS} months)")

    # No-leak rule: training targets must end strictly before the eval window starts.
    train_max_month = earliest_cutoff - pd.DateOffset(months=HORIZON_MONTHS)
    train_mask = (panel["date"] <= train_max_month) & panel["target"].notna()
    train_df = panel[train_mask].dropna(subset=REQUIRED_FOR_FIT).copy()
    train_df["zip_code"] = train_df["zip_code"].astype("category")
    train_df["home_type"] = train_df["home_type"].astype("category")
    print(f"  train rows: {len(train_df):,} (all ZIPs × home_types, months ≤ {train_max_month.date()})")

    X_train, y_train = train_df[feature_cols], train_df["target"]

    print(f"\nTraining LightGBM on {len(X_train):,} rows × {len(feature_cols)} features...")
    t1 = time.time()
    # Same hyperparams as production (see train_and_save_predictions) — reduced
    # trees + bagging because the typed panel is ~3× the size of the prior
    # single-type panel; backtest must match production for the numbers to mean
    # anything operationally.
    model = lgb.LGBMRegressor(
        n_estimators=250,
        learning_rate=0.05,
        num_leaves=63,
        min_child_samples=100,
        reg_lambda=0.1,
        subsample=0.7,
        subsample_freq=1,
        feature_fraction=0.9,
        n_jobs=-1,
        verbose=-1,
    )
    model.fit(X_train, y_train, categorical_feature=["zip_code", "home_type"])
    print(f"  trained in {time.time()-t1:.1f}s")

    # Keep the trained categories for consistent eval encoding.
    model._zip_categories = train_df["zip_code"].cat.categories
    model._home_type_categories = train_df["home_type"].cat.categories
    return model, panel, feature_cols, earliest_cutoff, latest_cutoff


def evaluate_sample(
    model: lgb.LGBMRegressor,
    panel: pd.DataFrame,
    feature_cols: list[str],
    earliest_cutoff: pd.Timestamp,
    latest_cutoff: pd.Timestamp,
    sample_n: int,
    seed: int,
) -> tuple[pd.DataFrame, dict]:
    """Score the trained model against a sampled subset of ZIPs."""
    eval_zips = _pick_eval_zips(panel, sample_n, seed)
    eval_mask = (
        panel["zip_code"].isin(eval_zips)
        & (panel["date"] >= earliest_cutoff)
        & (panel["date"] <= latest_cutoff)
        & panel["target"].notna()
    )
    eval_df = panel[eval_mask].dropna(subset=REQUIRED_FOR_FIT).copy()
    eval_df["zip_code"] = pd.Categorical(eval_df["zip_code"], categories=model._zip_categories)
    eval_df["home_type"] = pd.Categorical(eval_df["home_type"], categories=model._home_type_categories)

    X_eval = eval_df[feature_cols]
    eval_df["pred_growth"] = model.predict(X_eval)
    eval_df["pred_price_future"] = eval_df["median_value"] * (1 + eval_df["pred_growth"])
    eval_df["actual_price_future"] = eval_df["price_future"]
    eval_df["abs_pct_error"] = (
        (eval_df["pred_price_future"] - eval_df["actual_price_future"]).abs()
        / eval_df["actual_price_future"]
    )
    eval_df["signed_pct_error"] = (
        (eval_df["pred_price_future"] - eval_df["actual_price_future"])
        / eval_df["actual_price_future"]
    )
    eval_df["smape"] = (
        (eval_df["pred_price_future"] - eval_df["actual_price_future"]).abs()
        / ((eval_df["pred_price_future"].abs() + eval_df["actual_price_future"].abs()) / 2)
    )

    # Apples-to-apples slice: 'all'-type only. This is the metric comparable
    # to the v2/v3 baselines, since those models only saw the combined index.
    all_only = eval_df[eval_df["home_type"] == "all"]

    summary = {
        "seed": seed,
        "n": int(len(all_only)),
        "mape": float(all_only["abs_pct_error"].mean()) if len(all_only) else float("nan"),
        "smape": float(all_only["smape"].mean()) if len(all_only) else float("nan"),
        "bias": float(all_only["signed_pct_error"].mean()) if len(all_only) else float("nan"),
        # Per-home-type breakdown — useful for spotting that condo/SFR slices
        # behave differently than the all-homes index. Same eval ZIPs, just
        # scored on whichever home_type rows exist for them.
        "per_type": {
            ht: {
                "n": int((eval_df["home_type"] == ht).sum()),
                "mape": float(eval_df.loc[eval_df["home_type"] == ht, "abs_pct_error"].mean())
                    if (eval_df["home_type"] == ht).any() else float("nan"),
                "smape": float(eval_df.loc[eval_df["home_type"] == ht, "smape"].mean())
                    if (eval_df["home_type"] == ht).any() else float("nan"),
                "bias": float(eval_df.loc[eval_df["home_type"] == ht, "signed_pct_error"].mean())
                    if (eval_df["home_type"] == ht).any() else float("nan"),
            }
            for ht in VALID_HOME_TYPES
        },
    }
    return eval_df, summary


def _print_multi_seed(summaries: list[dict]) -> None:
    # ── Apples-to-apples slice (home_type='all') — comparable to prior baselines
    print("\nLightGBM panel — 12-month horizon (home_type='all', baseline-comparable)")
    print(f"  {'seed':>6}  {'n':>5}  {'MAPE':>7}  {'sMAPE':>7}  {'bias (ME)':>10}")
    print("  " + "-" * 44)
    for s in summaries:
        print(
            f"  {s['seed']:>6}  {s['n']:>5}  "
            f"{s['mape']*100:>6.2f}%  {s['smape']*100:>6.2f}%  "
            f"{s['bias']*100:>+9.2f}%"
        )
    if len(summaries) > 1:
        mape_mean = sum(s["mape"] for s in summaries) / len(summaries)
        bias_mean = sum(s["bias"] for s in summaries) / len(summaries)
        mape_spread = max(s["mape"] for s in summaries) - min(s["mape"] for s in summaries)
        bias_spread = max(s["bias"] for s in summaries) - min(s["bias"] for s in summaries)
        print(
            f"\n  Across {len(summaries)} seeds: "
            f"MAPE mean {mape_mean*100:.2f}% (spread {mape_spread*100:.2f}pp), "
            f"bias mean {bias_mean*100:+.2f}% (spread {bias_spread*100:.2f}pp)"
        )

    # ── Per-home-type breakdown — same eval ZIPs, sliced by type
    print("\nPer-home-type breakdown (same eval ZIPs, all sampled seeds averaged)")
    print(f"  {'home_type':<14}  {'n':>6}  {'MAPE':>7}  {'sMAPE':>7}  {'bias (ME)':>10}")
    print("  " + "-" * 52)
    for ht in VALID_HOME_TYPES:
        per = [s["per_type"].get(ht) for s in summaries if s.get("per_type", {}).get(ht)]
        per = [p for p in per if p and p["n"]]
        if not per:
            print(f"  {ht:<14}  {'—':>6}  {'—':>7}  {'—':>7}  {'—':>10}")
            continue
        n_total = sum(p["n"] for p in per)
        mape_avg = sum(p["mape"] * p["n"] for p in per) / n_total
        smape_avg = sum(p["smape"] * p["n"] for p in per) / n_total
        bias_avg = sum(p["bias"] * p["n"] for p in per) / n_total
        print(
            f"  {ht:<14}  {n_total:>6}  "
            f"{mape_avg*100:>6.2f}%  {smape_avg*100:>6.2f}%  "
            f"{bias_avg*100:>+9.2f}%"
        )

    print(
        "\n  Prior baselines (same protocol, seed=42):\n"
        "    Prophet+CAGR        MAPE 4.66%   bias +4.33%\n"
        "    LGBM v2 (supply)    MAPE 3.18%   bias  -0.62%"
    )


def train_and_save_predictions(engine=None) -> int:
    """Production path: train on ALL labeled data and persist a 12-month
    endpoint prediction for every ZIP.

    No held-out window — the backtest already validated the configuration;
    the serving model should use every label available. The Prophet
    projection service reads these rows to anchor its 12-month forecast.

    Returns the number of ZIPs written.
    """
    if engine is None:
        engine = create_engine(DATABASE_URL)

    print("Loading prices + macro and building features...")
    t0 = time.time()
    panel, feature_cols = build_panel(engine)
    print(f"  panel: {len(panel):,} rows in {time.time()-t0:.1f}s")

    # Train on every row that has a known 12-month target.
    train_df = panel[panel["target"].notna()].dropna(subset=REQUIRED_FOR_FIT).copy()
    train_df["zip_code"] = train_df["zip_code"].astype("category")
    train_df["home_type"] = train_df["home_type"].astype("category")
    print(f"  train rows: {len(train_df):,}")

    print(f"\nTraining LightGBM ({MODEL_VERSION})...")
    t1 = time.time()
    # Production model: reduced trees + bagging because the typed panel is ~3×
    # the size of the prior single-type panel (3 home_types stacked). Keeps
    # train time bounded without meaningfully changing the 12-month forecast.
    model = lgb.LGBMRegressor(
        n_estimators=250,
        learning_rate=0.05,
        num_leaves=63,
        min_child_samples=100,
        reg_lambda=0.1,
        subsample=0.7,
        subsample_freq=1,
        feature_fraction=0.9,
        n_jobs=-1,
        verbose=-1,
    )
    model.fit(
        train_df[feature_cols],
        train_df["target"],
        categorical_feature=["zip_code", "home_type"],
    )
    train_seconds = time.time() - t1
    print(f"  trained in {train_seconds:.1f}s")

    # Predict at the latest month per (zip, home_type) that has all features computable.
    pred_df = (
        panel.dropna(subset=feature_cols)
        .groupby(["zip_code", "home_type"], sort=False)
        .tail(1)
        .copy()
    )
    pred_df["zip_code"] = pd.Categorical(
        pred_df["zip_code"], categories=train_df["zip_code"].cat.categories
    )
    pred_df["home_type"] = pd.Categorical(
        pred_df["home_type"], categories=train_df["home_type"].cat.categories
    )
    # Drop (zip, home_type) combos the trained model didn't see (cold start).
    pred_df = pred_df[pred_df["zip_code"].notna() & pred_df["home_type"].notna()]
    pred_df["predicted_growth_12m"] = model.predict(pred_df[feature_cols])
    pred_df["predicted_endpoint_price"] = (
        pred_df["median_value"] * (1 + pred_df["predicted_growth_12m"])
    )
    # Count training rows per (zip, home_type) — data the prediction is grounded in.
    counts = (
        train_df.groupby(["zip_code", "home_type"], observed=True)
        .size()
        .to_dict()
    )

    now = datetime.utcnow()
    rows = [
        {
            "zip_code": str(r.zip_code),
            "home_type": str(r.home_type),
            "model_version": MODEL_VERSION,
            "trained_at": now,
            "reference_month": r.date.date(),
            "reference_price": float(r.median_value),
            "predicted_growth_12m": float(r.predicted_growth_12m),
            "predicted_endpoint_price": float(r.predicted_endpoint_price),
            "data_points_used": int(counts.get((r.zip_code, r.home_type), 0)),
        }
        for r in pred_df.itertuples(index=False)
    ]
    print(f"\nUpserting {len(rows):,} (ZIP × home_type) predictions...")

    # Upsert in batches — composite primary key is (zip_code, home_type).
    t2 = time.time()
    with engine.begin() as conn:
        for i in range(0, len(rows), 2000):
            chunk = rows[i:i + 2000]
            stmt = pg_insert(ZipLgbmPrediction.__table__).values(chunk)
            stmt = stmt.on_conflict_do_update(
                index_elements=["zip_code", "home_type"],
                set_={c: stmt.excluded[c] for c in (
                    "model_version", "trained_at", "reference_month",
                    "reference_price", "predicted_growth_12m",
                    "predicted_endpoint_price", "data_points_used",
                )},
            )
            conn.execute(stmt)
    print(f"  wrote {len(rows):,} rows in {time.time()-t2:.1f}s")

    # Record the run so the Methodology page can show users when and how the
    # served model was trained. Failures here shouldn't roll back the
    # predictions write — log and move on.
    try:
        with engine.begin() as conn:
            conn.execute(
                ModelRun.__table__.insert().values(
                    model_version=MODEL_VERSION,
                    trained_at=now,
                    panel_rows=int(len(panel)),
                    train_rows=int(len(train_df)),
                    feature_count=int(len(feature_cols)),
                    zips_predicted=int(len(rows)),
                    train_seconds=float(train_seconds),
                    notes="production retrain (--save-predictions)",
                )
            )
        print(f"  recorded run in model_runs")
    except Exception as exc:  # pragma: no cover — defensive
        print(f"  warning: failed to record model_run: {exc}")

    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Train + evaluate the LightGBM panel forecast")
    parser.add_argument("--sample", type=int, default=SAMPLE_DEFAULT)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--seeds", type=str, help="Comma-separated seeds (multi-seed robustness)")
    parser.add_argument("--csv", type=str, help="Write per-row predictions (seed=first) to this CSV")
    parser.add_argument(
        "--save-predictions",
        action="store_true",
        help="Production mode: train on ALL data and upsert predictions for every ZIP",
    )
    args = parser.parse_args()

    if args.save_predictions:
        n = train_and_save_predictions()
        print(f"\nWrote {n:,} ZIP predictions to zip_lgbm_predictions")
        return 0

    seeds = [int(s) for s in args.seeds.split(",")] if args.seeds else [args.seed]
    model, panel, feature_cols, earliest, latest = build_and_train()

    print(f"\nEvaluating against {len(seeds)} seed(s): {seeds}")
    summaries: list[dict] = []
    first_eval_df: pd.DataFrame | None = None
    for s in seeds:
        eval_df, summary = evaluate_sample(model, panel, feature_cols, earliest, latest, args.sample, s)
        summaries.append(summary)
        if first_eval_df is None:
            first_eval_df = eval_df

    _print_multi_seed(summaries)

    if args.csv and first_eval_df is not None:
        cols = ["zip_code", "date", "median_value", "actual_price_future",
                "pred_price_future", "abs_pct_error", "signed_pct_error", "smape"]
        first_eval_df[cols].to_csv(args.csv, index=False)
        print(f"\nWrote {len(first_eval_df)} rows to {args.csv} (seed={seeds[0]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

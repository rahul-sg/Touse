"""
Rolling-origin backtest harness for the ZIP-level price forecast.

For each ZIP, walks forward through history, training on each prefix and
predicting 1/3/6/12 months ahead, then compares to actuals. Aggregates MAPE,
sMAPE, and signed mean error per horizon — gives us a hard baseline number to
beat before changing the model.

CLI:
    python -m app.ml.backtest --sample 30
    python -m app.ml.backtest --zips 94566,78701,10001 --folds 12
    python -m app.ml.backtest --sample 100 --csv out.csv
"""
import argparse
import csv
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import date
from typing import Callable

import pandas as pd
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

# Make the backend/ root importable when run as `python -m app.ml.backtest`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.models.zip_price_history import ZipPriceHistory  # noqa: E402
from app.services.zip_projection import (  # noqa: E402
    _fit_and_forecast,
    FORECAST_MONTHS,
)

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://touse:touse@localhost:5433/touse",
).replace("postgresql+asyncpg://", "postgresql+psycopg2://")

DEFAULT_HORIZONS = (1, 3, 6, 12)
DEFAULT_FOLDS = 12
DEFAULT_MIN_TRAIN = 60   # 5 yrs — Prophet needs a few years to learn seasonality


@dataclass
class Observation:
    """One (cutoff, horizon) error observation for a single ZIP."""
    zip_code: str
    cutoff: date
    horizon_months: int
    actual: float
    predicted: float

    @property
    def abs_pct_error(self) -> float:
        return abs(self.predicted - self.actual) / self.actual if self.actual else 0.0

    @property
    def signed_pct_error(self) -> float:
        return (self.predicted - self.actual) / self.actual if self.actual else 0.0

    @property
    def smape(self) -> float:
        denom = (abs(self.predicted) + abs(self.actual)) / 2
        return abs(self.predicted - self.actual) / denom if denom else 0.0


def _load_zip_history(session: Session, zip_code: str) -> list[tuple[date, float]]:
    rows = session.execute(
        select(ZipPriceHistory.date, ZipPriceHistory.median_value)
        .where(
            ZipPriceHistory.zip_code == zip_code,
            ZipPriceHistory.median_value.isnot(None),
        )
        .order_by(ZipPriceHistory.date)
    ).all()
    return [(d, float(v)) for d, v in rows]


def backtest_zip(
    history: list[tuple[date, float]],
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    n_folds: int = DEFAULT_FOLDS,
    min_train_months: int = DEFAULT_MIN_TRAIN,
    model_fn: Callable = _fit_and_forecast,
    zip_code: str = "",
) -> list[Observation]:
    """Walk forward through history, fitting the model on each prefix and
    recording per-horizon prediction errors.
    """
    H = max(horizons)
    N = len(history)
    obs: list[Observation] = []
    for fold in range(n_folds):
        cutoff_idx = N - H - fold
        if cutoff_idx < min_train_months:
            break
        train = history[:cutoff_idx]
        cutoff_date = train[-1][0]
        try:
            points, _current, _pct = model_fn(train)
        except Exception:
            continue
        # The model returns a chart-ready list whose last FORECAST_MONTHS entries
        # are the projected months in order (t+1, t+2, ..., t+FORECAST_MONTHS).
        forecast_points = points[-FORECAST_MONTHS:]
        for h in horizons:
            if h > FORECAST_MONTHS:
                continue
            pred = float(forecast_points[h - 1]["price"])
            _, actual_val = history[cutoff_idx + h - 1]
            obs.append(Observation(
                zip_code=zip_code,
                cutoff=cutoff_date,
                horizon_months=h,
                actual=actual_val,
                predicted=pred,
            ))
    return obs


def summarize(obs: list[Observation]) -> dict:
    """Aggregate MAPE / sMAPE / signed mean error per horizon."""
    if not obs:
        return {}
    df = pd.DataFrame([{
        "h": o.horizon_months,
        "abs_pct": o.abs_pct_error,
        "signed_pct": o.signed_pct_error,
        "smape": o.smape,
    } for o in obs])
    grouped = df.groupby("h").agg(
        n=("abs_pct", "size"),
        mape=("abs_pct", "mean"),
        smape=("smape", "mean"),
        bias=("signed_pct", "mean"),
    ).to_dict("index")
    return {int(h): {k: float(v) for k, v in row.items()} for h, row in grouped.items()}


def _pick_zip_sample(session: Session, n: int, seed: int = 42) -> list[str]:
    """Random sample of ZIPs that have enough history to backtest fairly."""
    need = DEFAULT_MIN_TRAIN + max(DEFAULT_HORIZONS) + DEFAULT_FOLDS
    rows = session.execute(
        select(ZipPriceHistory.zip_code)
        .where(ZipPriceHistory.median_value.isnot(None))
        .group_by(ZipPriceHistory.zip_code)
        .having(func.count() >= need)
    ).scalars().all()
    random.seed(seed)
    return random.sample(rows, min(n, len(rows)))


def _format_summary(summary: dict, n_zips: int) -> str:
    if not summary:
        return "\n(no observations — every ZIP was skipped)"
    lines = [
        f"\nBacktest summary — current model (Prophet + CAGR blend) · {n_zips} ZIPs",
        f"{'horizon':>10}  {'n':>6}  {'MAPE':>8}  {'sMAPE':>8}  {'bias (ME)':>10}",
        "-" * 54,
    ]
    for h in sorted(summary):
        s = summary[h]
        lines.append(
            f"{h:>9}mo  {int(s['n']):>6}  "
            f"{s['mape']*100:>7.2f}%  {s['smape']*100:>7.2f}%  "
            f"{s['bias']*100:>+9.2f}%"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Rolling-origin backtest for the ZIP forecast")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--sample", type=int, help="Backtest N randomly-sampled ZIPs")
    g.add_argument("--zips", type=str, help="Comma-separated list of ZIPs to backtest")
    parser.add_argument("--folds", type=int, default=DEFAULT_FOLDS)
    parser.add_argument("--horizons", type=str, default="1,3,6,12")
    parser.add_argument("--csv", type=str, help="Write per-observation CSV here")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    horizons = tuple(int(h) for h in args.horizons.split(","))
    engine = create_engine(DATABASE_URL)

    with Session(engine) as session:
        if args.sample:
            zips = _pick_zip_sample(session, args.sample, args.seed)
        else:
            zips = [z.strip().zfill(5) for z in args.zips.split(",")]

        all_obs: list[Observation] = []
        t0 = time.time()
        for i, z in enumerate(zips, 1):
            history = _load_zip_history(session, z)
            if len(history) < DEFAULT_MIN_TRAIN + max(horizons):
                print(f"[{i}/{len(zips)}] {z}: skipped — only {len(history)} months")
                continue
            t1 = time.time()
            obs = backtest_zip(history, horizons=horizons, n_folds=args.folds, zip_code=z)
            all_obs.extend(obs)
            print(f"[{i}/{len(zips)}] {z}: {len(obs)} obs in {time.time()-t1:.1f}s")
        print(f"\nTotal {len(all_obs)} obs across {len(zips)} ZIPs in {time.time()-t0:.1f}s")

    summary = summarize(all_obs)
    print(_format_summary(summary, n_zips=len(zips)))

    if args.csv:
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow([
                "zip", "cutoff", "horizon_months", "actual", "predicted",
                "abs_pct_error", "signed_pct_error", "smape",
            ])
            for o in all_obs:
                w.writerow([
                    o.zip_code, o.cutoff.isoformat(), o.horizon_months,
                    o.actual, o.predicted, o.abs_pct_error, o.signed_pct_error, o.smape,
                ])
        print(f"Wrote {len(all_obs)} rows to {args.csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Bulk-train Prophet projections for every (zip, home_type) with an LGBM
prediction. Writes results to `zip_forecast_results` so the server can serve
them without having to fit Stan locally.

Designed to run on your dev machine where Stan is installed. Output is the
populated cache table — dump it and restore on the server with:

    pg_dump -U touse -d touse -t zip_forecast_results --data-only > forecasts.sql
    psql -U touse -d touse < forecasts.sql

Parallelism:
    --workers N    (default: half your CPU cores; Prophet is single-threaded
                    so spinning up workers gives near-linear speedup)

Filters:
    --home-type {all,single_family,condo}  (default: all 3)
    --limit N      (default: all eligible; useful for smoke-testing)
    --min-history MONTHS   (default: 60; ZIPs with less data are skipped)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, date
from multiprocessing import Pool, cpu_count

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session


DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://touse:touse@localhost:5433/touse",
).replace("postgresql+asyncpg://", "postgresql+psycopg2://")


# Per-worker engine, created lazily so each subprocess gets its own.
_WORKER_ENGINE = None


def _get_engine():
    global _WORKER_ENGINE
    if _WORKER_ENGINE is None:
        _WORKER_ENGINE = create_engine(DB_URL, pool_size=1, max_overflow=0)
    return _WORKER_ENGINE


def _fetch_one(zip_code: str, home_type: str) -> tuple | None:
    """Worker function — fits Prophet for one (zip, home_type) and returns
    an upsert tuple. Returns None if not enough history."""
    from app.models.zip_lgbm_prediction import ZipLgbmPrediction
    from app.models.zip_price_history import ZipPriceHistory
    from app.services.zip_projection import _fit_and_forecast, MODEL_VERSION, MIN_MONTHS

    engine = _get_engine()
    with Session(engine) as session:
        rows = session.execute(
            select(ZipPriceHistory.date, ZipPriceHistory.median_value)
            .where(
                ZipPriceHistory.zip_code == zip_code,
                ZipPriceHistory.home_type == home_type,
                ZipPriceHistory.median_value.isnot(None),
            )
            .order_by(ZipPriceHistory.date)
        ).all()
        history = [(d, float(v)) for d, v in rows]
        if len(history) < MIN_MONTHS:
            return None

        lgbm = session.execute(
            select(ZipLgbmPrediction).where(
                ZipLgbmPrediction.zip_code == zip_code,
                ZipLgbmPrediction.home_type == home_type,
            )
        ).scalar_one_or_none()
        anchor = float(lgbm.predicted_endpoint_price) if lgbm else None

        try:
            points, current_value, pct = _fit_and_forecast(history, anchor)
        except Exception as exc:  # noqa: BLE001
            print(f"  fit failed for {zip_code}/{home_type}: {exc}", file=sys.stderr)
            return None

        return (zip_code, home_type, MODEL_VERSION, datetime.utcnow(),
                current_value, pct, len(history), points)


def _worker(args):
    zip_code, home_type = args
    return _fetch_one(zip_code, home_type)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=max(1, cpu_count() // 2))
    parser.add_argument("--home-type", choices=["all", "single_family", "condo"], default=None,
                        help="Restrict to one home type (default: all 3)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Stop after N pairs (smoke-test)")
    parser.add_argument("--min-history", type=int, default=60,
                        help="Skip ZIPs with fewer months of data")
    args = parser.parse_args()

    # Gather work units from the LGBM predictions table — those are the
    # (zip, home_type) pairs we actually have anchors for.
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        sql = "SELECT zip_code, home_type FROM zip_lgbm_predictions"
        if args.home_type:
            sql += f" WHERE home_type = '{args.home_type}'"
        sql += " ORDER BY zip_code, home_type"
        pairs = [(z, h) for z, h in conn.execute(text(sql)).all()]

    if args.limit:
        pairs = pairs[:args.limit]

    print(f"Training Prophet for {len(pairs):,} (zip, home_type) pairs with {args.workers} workers")
    t0 = time.time()

    upserts = []
    with Pool(args.workers) as pool:
        for i, result in enumerate(pool.imap_unordered(_worker, pairs, chunksize=4), 1):
            if result is not None:
                upserts.append(result)
            if i % 100 == 0 or i == len(pairs):
                elapsed = time.time() - t0
                rate = i / elapsed
                eta = (len(pairs) - i) / rate if rate else 0
                print(f"  {i:,}/{len(pairs):,}  ({rate:.1f}/s, ETA {eta/60:.1f} min, {len(upserts):,} successful)")

    # Bulk upsert
    print(f"\nUpserting {len(upserts):,} rows into zip_forecast_results...")
    t1 = time.time()
    with engine.begin() as conn:
        # Postgres ON CONFLICT requires unique index — we have one on (zip_code, home_type)
        conn.execute(text("""
            CREATE TEMP TABLE _tmp_forecasts (
                zip_code VARCHAR(10),
                home_type VARCHAR(20),
                model_version VARCHAR(32),
                trained_at TIMESTAMP,
                current_value FLOAT,
                forecast_12m_pct FLOAT,
                data_points INTEGER,
                forecast_12m JSON
            )
        """))
        # Insert via executemany — fast enough for ~50k rows
        import json
        conn.execute(
            text("""INSERT INTO _tmp_forecasts VALUES
                    (:z, :h, :mv, :t, :cv, :pct, :n, CAST(:pts AS JSON))"""),
            [{"z": z, "h": h, "mv": mv, "t": t, "cv": cv, "pct": pct, "n": n,
              "pts": json.dumps(pts)} for z, h, mv, t, cv, pct, n, pts in upserts],
        )
        conn.execute(text("""
            INSERT INTO zip_forecast_results
                (zip_code, home_type, model_version, trained_at,
                 current_value, forecast_12m_pct, data_points, forecast_12m)
            SELECT zip_code, home_type, model_version, trained_at,
                   current_value, forecast_12m_pct, data_points, forecast_12m
            FROM _tmp_forecasts
            ON CONFLICT (zip_code, home_type) DO UPDATE SET
                model_version = EXCLUDED.model_version,
                trained_at = EXCLUDED.trained_at,
                current_value = EXCLUDED.current_value,
                forecast_12m_pct = EXCLUDED.forecast_12m_pct,
                data_points = EXCLUDED.data_points,
                forecast_12m = EXCLUDED.forecast_12m
        """))
    print(f"  wrote in {time.time()-t1:.1f}s")
    print(f"\nDone — total time {(time.time()-t0)/60:.1f} min")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

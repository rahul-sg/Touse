"""
FRED API ingestion.
Fetches CPI, housing starts, Fed funds rate, unemployment. Requires FRED_API_KEY.

NOTE: the 30-year mortgage rate is NOT pulled here — it comes from Freddie Mac's
key-free PMMS feed (see etl/freddie_mac.py), the authoritative survey FRED itself
mirrors. This keeps the live mortgage rate working without any API key.
Source: https://fred.stlouisfed.org/docs/api/fred/
"""
import os
from datetime import datetime
import requests
import pandas as pd
from sqlalchemy.dialects.postgresql import insert

from app.models.macro_indicator import MacroIndicator
from etl.db import get_session

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")

# mortgage_rate_30y intentionally omitted — see etl/freddie_mac.py
SERIES = {
    "fed_funds_rate": "FEDFUNDS",
    "cpi": "CPIAUCSL",
    "housing_starts": "HOUST",
    "unemployment": "UNRATE",
}


def fetch_series(series_id: str, observation_start: str = "2000-01-01") -> pd.DataFrame:
    resp = requests.get(FRED_BASE, params={
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": observation_start,
    })
    resp.raise_for_status()
    data = resp.json()["observations"]
    df = pd.DataFrame(data)[["date", "value"]]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna()


def load_to_db(series_name: str, df: pd.DataFrame) -> None:
    session = get_session()
    try:
        batch = [
            {
                "series_name": series_name,
                "geo_id": "US",
                "date": row["date"].date(),
                "value": float(row["value"]),
                "source": "FRED",
            }
            for _, row in df.iterrows()
        ]
        stmt = insert(MacroIndicator).values(batch).on_conflict_do_update(
            constraint="uq_series_geo_date",
            set_={"value": insert(MacroIndicator).excluded.value},
        )
        session.execute(stmt)
        session.commit()
        print(f"Loaded {len(batch)} rows for {series_name}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def run_all() -> None:
    for name, sid in SERIES.items():
        print(f"Fetching {name} ({sid})...")
        df = fetch_series(sid)
        load_to_db(name, df)


if __name__ == "__main__":
    run_all()

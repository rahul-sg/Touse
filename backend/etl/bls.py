"""
BLS API ingestion — metro-level unemployment.
Series IDs follow the pattern LAUMT{FIPS}0000000003 for metro unemployment rate.
Source: https://www.bls.gov/developers/
"""
import os
from datetime import date
import requests
import pandas as pd
from sqlalchemy.dialects.postgresql import insert

from app.models.macro_indicator import MacroIndicator
from etl.db import get_session

BLS_API_KEY = os.environ.get("BLS_API_KEY", "")
BLS_BASE = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

# National unemployment — state-level handled by FRED; metro-level requires BLS series IDs
# Add metro series IDs here as the regions table is populated
NATIONAL_SERIES = {
    "unemployment_national": "LNS14000000",
}


def fetch_series(series_ids: list[str], start_year: str = "2000", end_year: str = "2025") -> list[dict]:
    payload = {
        "seriesid": series_ids,
        "startyear": start_year,
        "endyear": end_year,
        "registrationkey": BLS_API_KEY,
    }
    resp = requests.post(BLS_BASE, json=payload)
    resp.raise_for_status()
    rows = []
    for series in resp.json()["Results"]["series"]:
        sid = series["seriesID"]
        for obs in series["data"]:
            if not obs["period"].startswith("M"):
                continue
            month = int(obs["period"][1:])
            rows.append({
                "series_id": sid,
                "date": date(int(obs["year"]), month, 1),
                "value": float(obs["value"]),
            })
    return rows


def load_to_db(series_name: str, rows: list[dict], geo_id: str = "US") -> None:
    session = get_session()
    try:
        batch = [
            {
                "series_name": series_name,
                "geo_id": geo_id,
                "date": r["date"],
                "value": r["value"],
                "source": "BLS",
            }
            for r in rows
        ]
        stmt = insert(MacroIndicator).values(batch).on_conflict_do_update(
            constraint="uq_series_geo_date",
            set_={"value": insert(MacroIndicator).excluded.value},
        )
        session.execute(stmt)
        session.commit()
        print(f"Loaded {len(batch)} rows for {series_name} ({geo_id})")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def run_all() -> None:
    for name, sid in NATIONAL_SERIES.items():
        print(f"Fetching {name} ({sid})...")
        rows = fetch_series([sid])
        load_to_db(name, rows, geo_id="US")


if __name__ == "__main__":
    run_all()

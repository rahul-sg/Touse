"""
Freddie Mac PMMS (Primary Mortgage Market Survey) ingestion.

Pulls the weekly 30-year and 15-year fixed mortgage rate history straight from
Freddie Mac's public CSV. No API key required — this is the same survey that
FRED's MORTGAGE30US series mirrors, so it is the authoritative live source.

Run directly:
    python3 -m etl.freddie_mac

Source: https://www.freddiemac.com/pmms
"""
import io
import sys
import os
import requests
import pandas as pd
from sqlalchemy.dialects.postgresql import insert

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.macro_indicator import MacroIndicator
from etl.db import get_session

PMMS_URL = "https://www.freddiemac.com/pmms/docs/PMMS_history.csv"

# CSV column -> macro_indicators.series_name
SERIES = {
    "pmms30": "mortgage_rate_30y",
    "pmms15": "mortgage_rate_15y",
}


def fetch_pmms() -> pd.DataFrame:
    """Download and parse the full PMMS history CSV."""
    resp = requests.get(PMMS_URL, timeout=30, headers={"User-Agent": "touse-etl/1.0"})
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    # PMMS dates look like "4/2/1971" — month/day/year, no leading zeros.
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y", errors="coerce")
    df = df.dropna(subset=["date"])
    return df


def load_series(session, csv_col: str, series_name: str, df: pd.DataFrame) -> int:
    """Upsert one rate series into macro_indicators. Returns rows written."""
    sub = df[["date", csv_col]].copy()
    sub[csv_col] = pd.to_numeric(sub[csv_col], errors="coerce")
    sub = sub.dropna(subset=[csv_col])
    if sub.empty:
        return 0

    batch = [
        {
            "series_name": series_name,
            "geo_id": "US",
            "date": row["date"].date(),
            "value": float(row[csv_col]),
            "source": "FreddieMac",
        }
        for _, row in sub.iterrows()
    ]
    stmt = insert(MacroIndicator).values(batch).on_conflict_do_update(
        constraint="uq_series_geo_date",
        set_={"value": insert(MacroIndicator).excluded.value},
    )
    session.execute(stmt)
    session.commit()
    return len(batch)


def run() -> None:
    print(f"Fetching Freddie Mac PMMS history from {PMMS_URL} ...")
    df = fetch_pmms()
    print(f"  Parsed {len(df)} weekly observations.")

    session = get_session()
    try:
        for csv_col, series_name in SERIES.items():
            n = load_series(session, csv_col, series_name, df)
            print(f"  Loaded {n} rows for {series_name}")
        # Report the latest 30-year rate so the run is self-verifying.
        latest = (
            df.dropna(subset=["pmms30"]).sort_values("date").iloc[-1]
            if "pmms30" in df.columns else None
        )
        if latest is not None:
            print(f"  Latest 30-yr fixed: {latest['pmms30']}% (week of {latest['date'].date()})")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run()

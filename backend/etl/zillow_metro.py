"""
Zillow Research metro supply/demand ETL.

Pulls five monthly metro-level indicators from Zillow Research's public CSVs
and loads them into `metro_supply_history`:

  - invt_fs            : active for-sale inventory (smoothed)
  - new_listings       : newly listed homes per month
  - mean_doz_pending   : mean days on market before pending
  - perc_price_cut     : % of listings with a price cut
  - median_list_price  : median list price

Metro names are normalized to Zillow's short form ("San Francisco, CA") so they
join cleanly to zip_price_history.metro (which uses the long CBSA form like
"San Francisco-Oakland-Berkeley, CA") via the same normalization on the read side.

No API key required.

Run directly:
    python -m etl.zillow_metro
"""
import io
import os
import re
import sys

import pandas as pd
import requests
from sqlalchemy.dialects.postgresql import insert

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.metro_supply_history import MetroSupplyHistory
from etl.db import get_session

BASE = "https://files.zillowstatic.com/research/public_csvs/"
SOURCES = {
    "invt_fs":            "invt_fs/Metro_invt_fs_uc_sfrcondo_sm_month.csv",
    "new_listings":       "new_listings/Metro_new_listings_uc_sfrcondo_sm_month.csv",
    "mean_doz_pending":   "mean_doz_pending/Metro_mean_doz_pending_uc_sfrcondo_sm_month.csv",
    "perc_price_cut":     "perc_listings_price_cut/Metro_perc_listings_price_cut_uc_sfrcondo_sm_month.csv",
    "median_list_price":  "mlp/Metro_mlp_uc_sfrcondo_sm_month.csv",
    "median_rent":        "zori/Metro_zori_uc_sfrcondomfr_sm_month.csv",
}
_DATE_COL = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def normalize_metro(name: str) -> str:
    """Reduce a CBSA name to Zillow's short form.

    "San Francisco-Oakland-Berkeley, CA" → "San Francisco, CA"
    "New York-Newark-Jersey City, NY-NJ-PA" → "New York, NY"
    "San Francisco, CA" → "San Francisco, CA"
    """
    if not name or "," not in name:
        return (name or "").strip()
    head, state = name.rsplit(",", 1)
    primary_city = head.split("-")[0].strip()
    primary_state = state.strip().split("-")[0].strip()
    return f"{primary_city}, {primary_state}"


def fetch_and_melt(metric: str, path: str) -> pd.DataFrame:
    """Download one Zillow Research CSV → long format (metro, date, <metric>)."""
    resp = requests.get(BASE + path, timeout=60, headers={"User-Agent": "touse-etl/1.0"})
    resp.raise_for_status()
    df = pd.read_csv(io.StringIO(resp.text))
    df = df[df["RegionType"] == "msa"].copy()
    df["metro"] = df["RegionName"].map(normalize_metro)

    date_cols = [c for c in df.columns if _DATE_COL.match(c)]
    long = df.melt(id_vars=["metro"], value_vars=date_cols, var_name="date", value_name=metric)
    long["date"] = pd.to_datetime(long["date"]).dt.date
    long = long.dropna(subset=[metric])
    return long


def run() -> None:
    print("Fetching Zillow Research metro supply CSVs...")
    parts: list[pd.DataFrame] = []
    for metric, path in SOURCES.items():
        long = fetch_and_melt(metric, path)
        print(f"  {metric:18s}: {len(long):>7,} (metro, month) rows")
        parts.append(long)

    # Outer-merge all metrics on (metro, date).
    merged = parts[0]
    for p in parts[1:]:
        merged = merged.merge(p, on=["metro", "date"], how="outer")
    # Replace NaN with None for SQL nullability.
    merged = merged.where(pd.notna(merged), None)
    rows = merged.to_dict(orient="records")
    print(f"\nUpserting {len(rows):,} (metro, month) rows...")

    session = get_session()
    try:
        cols_to_update = ("invt_fs", "new_listings", "mean_doz_pending",
                          "perc_price_cut", "median_list_price", "median_rent")
        # Chunked upsert — keeps the statement size sane.
        for i in range(0, len(rows), 2000):
            chunk = rows[i:i + 2000]
            stmt = insert(MetroSupplyHistory).values(chunk).on_conflict_do_update(
                constraint="uq_metro_supply_metro_date",
                set_={c: insert(MetroSupplyHistory).excluded[c] for c in cols_to_update},
            )
            session.execute(stmt)
        session.commit()
        print(f"  wrote {len(rows):,} rows to metro_supply_history")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run()

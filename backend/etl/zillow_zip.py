"""
Zillow ZIP-level ZHVI ingestion.

Downloads the Zillow Home Value Index (ZHVI) CSV at ZIP code granularity
and loads it into the zip_price_history table.

Usage:
    DATABASE_URL=postgresql+asyncpg://... python3 -m etl.zillow_zip
"""
import pandas as pd
from sqlalchemy import text
from etl.db import get_session

# Each (home_type → ZHVI CSV URL). Zillow does NOT publish a ZIP-level
# townhouse-only index — that's bundled into the SFR series.
ZILLOW_ZIP_ZHVI_URLS = {
    "all":           "https://files.zillowstatic.com/research/public_csvs/zhvi/"
                     "Zip_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv",
    "single_family": "https://files.zillowstatic.com/research/public_csvs/zhvi/"
                     "Zip_zhvi_uc_sfr_sm_sa_month.csv",
    "condo":         "https://files.zillowstatic.com/research/public_csvs/zhvi/"
                     "Zip_zhvi_uc_condo_sm_sa_month.csv",
}

ZIP_ID_COLS = [
    "RegionID", "SizeRank", "RegionName", "RegionType",
    "StateName", "State", "City", "Metro", "CountyName",
]

BATCH_SIZE = 500


def fetch_zip_prices(url: str) -> pd.DataFrame:
    print(f"  downloading {url.rsplit('/', 1)[-1]} …")
    df = pd.read_csv(url, dtype={"RegionName": str})
    id_cols = [c for c in ZIP_ID_COLS if c in df.columns]
    date_cols = [c for c in df.columns if c not in id_cols]

    df_long = df.melt(
        id_vars=id_cols,
        value_vars=date_cols,
        var_name="date",
        value_name="median_value",
    )
    df_long["date"] = pd.to_datetime(df_long["date"], errors="coerce")
    df_long = df_long.dropna(subset=["median_value", "date"])
    df_long["zip_code"] = df_long["RegionName"].astype(str).str.zfill(5)

    col_map = {"StateName": "state_name", "State": "state", "City": "city", "Metro": "metro"}
    df_long = df_long.rename(columns={k: v for k, v in col_map.items() if k in df_long.columns})

    keep = ["zip_code", "date", "median_value", "city", "state", "metro"]
    available = [c for c in keep if c in df_long.columns]
    return df_long[available].reset_index(drop=True)


def _upsert(session, df: pd.DataFrame, home_type: str) -> None:
    total = len(df)
    print(f"  loading {total:,} rows for home_type={home_type!r}")
    for i in range(0, total, BATCH_SIZE):
        batch = df.iloc[i : i + BATCH_SIZE]
        rows = []
        for _, row in batch.iterrows():
            rows.append({
                "zip_code": str(row["zip_code"]),
                "home_type": home_type,
                "date": row["date"].date(),
                "median_value": float(row["median_value"]),
                "city": str(row["city"]) if "city" in row and pd.notna(row["city"]) else None,
                "state": str(row["state"]) if "state" in row and pd.notna(row["state"]) else None,
                "metro": str(row["metro"]) if "metro" in row and pd.notna(row["metro"]) else None,
            })

        session.execute(
            text(
                "INSERT INTO zip_price_history "
                "(zip_code, home_type, date, median_value, city, state, metro) "
                "VALUES (:zip_code, :home_type, :date, :median_value, :city, :state, :metro) "
                "ON CONFLICT (zip_code, home_type, date) DO UPDATE SET "
                "median_value = EXCLUDED.median_value, "
                "city = EXCLUDED.city, state = EXCLUDED.state, metro = EXCLUDED.metro"
            ),
            rows,
        )
        session.commit()

        if (i // BATCH_SIZE) % 80 == 0:
            pct = min(100, round((i + BATCH_SIZE) / total * 100))
            print(f"    {home_type}: {pct}% ({i + BATCH_SIZE:,}/{total:,})")


def load_zip_prices() -> None:
    print("Loading Zillow ZHVI per home type ('all', 'single_family', 'condo')")
    session = get_session()
    try:
        for home_type, url in ZILLOW_ZIP_ZHVI_URLS.items():
            df = fetch_zip_prices(url)
            _upsert(session, df, home_type)
        print("Done — per-type ZIP price history loaded.")
    finally:
        session.close()


if __name__ == "__main__":
    load_zip_prices()

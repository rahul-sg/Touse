"""
Zillow Research CSV ingestion.
Downloads monthly median sale price data by metro and loads into PostgreSQL.
Source: https://www.zillow.com/research/data/
"""
import pandas as pd
from sqlalchemy.dialects.postgresql import insert

from app.models.price_history import MetroPriceHistory
from app.models.region import Region
from etl.db import get_session

ZILLOW_METRO_URL = (
    "https://files.zillowstatic.com/research/public_csvs/zhvi/"
    "Metro_zhvi_uc_sfrcondo_tier_0.33_0.67_sm_sa_month.csv"
)

ID_COLS = [
    "RegionID", "SizeRank", "RegionName", "RegionType",
    "StateName", "Metro", "StateCodeFIPS", "MunicipalCodeFIPS",
]


def fetch_metro_prices() -> pd.DataFrame:
    df = pd.read_csv(ZILLOW_METRO_URL)
    date_cols = [c for c in df.columns if c not in ID_COLS]
    df_long = df.melt(
        id_vars=ID_COLS,
        value_vars=date_cols,
        var_name="date",
        value_name="median_price",
    )
    df_long["date"] = pd.to_datetime(df_long["date"])
    return df_long.dropna(subset=["median_price"])


def _metro_id(row: pd.Series) -> str:
    name = row["RegionName"].replace(", ", "-").replace(" ", "_").lower()
    return f"{name}"


def load_to_db(df: pd.DataFrame) -> None:
    session = get_session()
    try:
        # Upsert regions first
        regions = (
            df[["RegionID", "RegionName", "StateName"]]
            .drop_duplicates("RegionID")
        )
        for _, row in regions.iterrows():
            metro_id = _metro_id(row)
            state = row["StateName"][:2].upper() if pd.notna(row["StateName"]) else "US"
            stmt = insert(Region).values(
                metro_id=metro_id,
                name=row["RegionName"],
                state=state,
                state_name=row["StateName"] if pd.notna(row["StateName"]) else None,
                zillow_region_id=str(row["RegionID"]),
            ).on_conflict_do_update(
                index_elements=["metro_id"],
                set_={"name": row["RegionName"], "zillow_region_id": str(row["RegionID"])},
            )
            session.execute(stmt)

        # Upsert price history in batches
        batch = []
        for _, row in df.iterrows():
            batch.append({
                "metro_id": _metro_id(row),
                "date": row["date"].date(),
                "median_price": float(row["median_price"]),
                "zillow_region_id": str(row["RegionID"]),
            })
            if len(batch) >= 1000:
                stmt = insert(MetroPriceHistory).values(batch).on_conflict_do_nothing(
                    constraint="uq_metro_date"
                )
                session.execute(stmt)
                session.commit()
                batch = []

        if batch:
            stmt = insert(MetroPriceHistory).values(batch).on_conflict_do_nothing(
                constraint="uq_metro_date"
            )
            session.execute(stmt)
            session.commit()

        print(f"Loaded {len(df)} price history rows")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print("Fetching Zillow metro prices...")
    df = fetch_metro_prices()
    print(f"Fetched {len(df)} rows across {df['RegionName'].nunique()} metros")
    load_to_db(df)

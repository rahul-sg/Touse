"""
Zillow Research CSV ingestion.
Downloads monthly median sale price data and supply signals by metro,
and loads them into PostgreSQL.
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

# Supply signal CSVs (all free, no API key required)
ZILLOW_ACTIVE_LISTINGS_URL = (
    "https://files.zillowstatic.com/research/public_csvs/active_listings/"
    "Metro_active_listings_uc_sfrcondo_sm_month.csv"
)
ZILLOW_MEDIAN_DOM_URL = (
    "https://files.zillowstatic.com/research/public_csvs/days_on_market/"
    "Metro_median_dom_uc_sfrcondo_sm_month.csv"
)
ZILLOW_PRICE_CUT_URL = (
    "https://files.zillowstatic.com/research/public_csvs/perc_listings_price_cut/"
    "Metro_perc_listings_price_cut_uc_sfrcondo_sm_month.csv"
)

ID_COLS = [
    "RegionID", "SizeRank", "RegionName", "RegionType",
    "StateName", "Metro", "StateCodeFIPS", "MunicipalCodeFIPS",
]


def _metro_id(row: pd.Series) -> str:
    name = row["RegionName"].replace(", ", "-").replace(" ", "_").lower()
    return f"{name}"


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


def _fetch_supply_signal(url: str, value_name: str) -> pd.DataFrame:
    """Generic helper: fetch a Zillow supply CSV and melt to long form."""
    try:
        df = pd.read_csv(url)
    except Exception as e:
        print(f"[zillow] Warning — could not fetch {url}: {e}")
        return pd.DataFrame(columns=["RegionID", "RegionName", "date", value_name])

    id_cols_present = [c for c in ID_COLS if c in df.columns]
    date_cols = [c for c in df.columns if c not in ID_COLS]
    df_long = df.melt(
        id_vars=id_cols_present,
        value_vars=date_cols,
        var_name="date",
        value_name=value_name,
    )
    df_long["date"] = pd.to_datetime(df_long["date"])
    return df_long.dropna(subset=[value_name])


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


def load_supply_signals_to_db(
    active_listings_df: pd.DataFrame,
    median_dom_df: pd.DataFrame,
    price_cut_df: pd.DataFrame,
) -> None:
    """
    Merge supply signals onto existing metro_price_history rows via UPDATE.
    Matches on (metro_id, date). Only updates rows that already exist.
    """
    from sqlalchemy import text

    session = get_session()
    try:
        def _build_lookup(df: pd.DataFrame, col: str) -> dict:
            """Returns {(metro_id_str, date_str): value} from a supply signal DataFrame."""
            result = {}
            for _, row in df.iterrows():
                if "RegionName" not in row:
                    continue
                mid = row["RegionName"].replace(", ", "-").replace(" ", "_").lower()
                date_str = row["date"].date().isoformat()
                result[(mid, date_str)] = row[col]
            return result

        al_lookup = _build_lookup(active_listings_df, "active_listings")
        dom_lookup = _build_lookup(median_dom_df, "median_dom")
        pcut_lookup = _build_lookup(price_cut_df, "price_cut_pct")

        # Collect all (metro_id, date) keys across all three signals
        all_keys = set(al_lookup) | set(dom_lookup) | set(pcut_lookup)

        updated = 0
        batch_size = 500
        keys_list = list(all_keys)
        for i in range(0, len(keys_list), batch_size):
            chunk = keys_list[i : i + batch_size]
            for metro_id, date_str in chunk:
                al  = al_lookup.get((metro_id, date_str))
                dom = dom_lookup.get((metro_id, date_str))
                pct = pcut_lookup.get((metro_id, date_str))

                set_parts = []
                params: dict = {"metro_id": metro_id, "date": date_str}
                if al is not None:
                    set_parts.append("active_listings = :active_listings")
                    params["active_listings"] = int(al)
                if dom is not None:
                    set_parts.append("median_dom = :median_dom")
                    params["median_dom"] = float(dom)
                if pct is not None:
                    set_parts.append("price_cut_pct = :price_cut_pct")
                    params["price_cut_pct"] = float(pct)

                if not set_parts:
                    continue

                session.execute(
                    text(
                        f"UPDATE metro_price_history "
                        f"SET {', '.join(set_parts)} "
                        f"WHERE metro_id = :metro_id AND date = :date"
                    ),
                    params,
                )
                updated += 1

            session.commit()

        print(f"Updated supply signals for {updated} (metro, date) pairs")
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

    print("Fetching Zillow supply signals...")
    al_df = _fetch_supply_signal(ZILLOW_ACTIVE_LISTINGS_URL, "active_listings")
    dom_df = _fetch_supply_signal(ZILLOW_MEDIAN_DOM_URL, "median_dom")
    pcut_df = _fetch_supply_signal(ZILLOW_PRICE_CUT_URL, "price_cut_pct")
    print(
        f"  active_listings: {len(al_df)} rows | "
        f"median_dom: {len(dom_df)} rows | "
        f"price_cut_pct: {len(pcut_df)} rows"
    )
    load_supply_signals_to_db(al_df, dom_df, pcut_df)

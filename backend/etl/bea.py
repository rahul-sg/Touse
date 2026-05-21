"""
BEA API ingestion — state-level GDP growth (annual).
Source: https://apps.bea.gov/API/
"""
import os
from datetime import date
import requests
import pandas as pd
from sqlalchemy.dialects.postgresql import insert

from app.models.macro_indicator import MacroIndicator
from etl.db import get_session

BEA_API_KEY = os.environ.get("BEA_API_KEY", "")
BEA_BASE = "https://apps.bea.gov/api/data"

STATE_FIPS_TO_CODE = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA",
    "08": "CO", "09": "CT", "10": "DE", "12": "FL", "13": "GA",
    "15": "HI", "16": "ID", "17": "IL", "18": "IN", "19": "IA",
    "20": "KS", "21": "KY", "22": "LA", "23": "ME", "24": "MD",
    "25": "MA", "26": "MI", "27": "MN", "28": "MS", "29": "MO",
    "30": "MT", "31": "NE", "32": "NV", "33": "NH", "34": "NJ",
    "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC",
    "46": "SD", "47": "TN", "48": "TX", "49": "UT", "50": "VT",
    "51": "VA", "53": "WA", "54": "WV", "55": "WI", "56": "WY",
}

START_YEAR = 2000
END_YEAR = 2024


def fetch_state_gdp() -> pd.DataFrame:
    year_str = ",".join(str(y) for y in range(START_YEAR, END_YEAR + 1))
    params = {
        "UserID": BEA_API_KEY,
        "method": "GetData",
        "datasetname": "Regional",
        "TableName": "SAGDP9",  # Real GDP by state, annual (chained dollars)
        "LineCode": "1",        # all-industry total
        "GeoFips": "STATE",
        "Year": year_str,
        "ResultFormat": "JSON",
    }
    resp = requests.get(BEA_BASE, params=params)
    resp.raise_for_status()
    data = resp.json()["BEAAPI"]["Results"]["Data"]
    df = pd.DataFrame(data)
    df["DataValue"] = pd.to_numeric(
        df["DataValue"].astype(str).str.replace(",", ""), errors="coerce"
    )
    df = df.dropna(subset=["DataValue"])
    df["Year"] = df["TimePeriod"].astype(int)
    # BEA returns 5-digit GeoFips for states ("SS000"); take the 2-digit state code.
    df["GeoFips"] = df["GeoFips"].astype(str).str.zfill(5).str[:2]
    return df


def load_to_db(df: pd.DataFrame) -> None:
    session = get_session()
    try:
        # Compute YoY growth per state
        df_sorted = df.sort_values(["GeoFips", "Year"])
        df_sorted["gdp_growth"] = df_sorted.groupby("GeoFips")["DataValue"].pct_change() * 100

        batch = []
        for _, row in df_sorted.dropna(subset=["gdp_growth"]).iterrows():
            state_code = STATE_FIPS_TO_CODE.get(row["GeoFips"])
            if not state_code:
                continue
            batch.append({
                "series_name": "gdp_growth",
                "geo_id": state_code,
                "date": date(int(row["Year"]), 1, 1),
                "value": float(row["gdp_growth"]),
                "source": "BEA",
            })

        stmt = insert(MacroIndicator).values(batch).on_conflict_do_update(
            constraint="uq_series_geo_date",
            set_={"value": insert(MacroIndicator).excluded.value},
        )
        session.execute(stmt)
        session.commit()
        print(f"Loaded {len(batch)} GDP growth rows")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    print("Fetching BEA state GDP...")
    df = fetch_state_gdp()
    load_to_db(df)

"""
Census ACS ingestion.
Fetches population and median household income by ZIP code.
Source: https://www.census.gov/data/developers/data-sets/acs-5year.html
"""
import os
import requests
import pandas as pd

CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY", "")
CENSUS_BASE = "https://api.census.gov/data"


def fetch_zip_demographics(year: int = 2022) -> pd.DataFrame:
    url = f"{CENSUS_BASE}/{year}/acs/acs5"
    params = {
        "get": "B19013_001E,B01003_001E",  # median income, total population
        "for": "zip code tabulation area:*",
        "key": CENSUS_API_KEY,
    }
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    data = resp.json()
    df = pd.DataFrame(data[1:], columns=data[0])
    df.rename(columns={
        "B19013_001E": "median_household_income",
        "B01003_001E": "population",
        "zip code tabulation area": "zip_code",
    }, inplace=True)
    df["median_household_income"] = pd.to_numeric(df["median_household_income"], errors="coerce")
    df["population"] = pd.to_numeric(df["population"], errors="coerce")
    return df


def load_to_db(df: pd.DataFrame) -> None:
    # TODO: upsert into regions table
    raise NotImplementedError

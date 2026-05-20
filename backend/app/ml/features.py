"""
Feature engineering for the LightGBM price forecast model.

Joins metro price history with macro indicators and policy flags into a
flat feature matrix. Each row is one (metro, month) observation.

Feature groups:
  - Price momentum: lags + rolling averages of the target (median_price)
  - Macro: mortgage rate, CPI, housing starts, unemployment, GDP growth
    (all with 1-2 month lags to prevent leakage)
  - Policy: zoning reform score, buyer credit, housing bond, election year
  - Calendar: month_of_year (captures seasonality without Prophet)
  - Identity: metro_id as LightGBM categorical
"""
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Lag helpers
def _lag(df: pd.DataFrame, col: str, n: int) -> pd.Series:
    return df.groupby("metro_id")[col].shift(n)

def _rolling(df: pd.DataFrame, col: str, window: int) -> pd.Series:
    return df.groupby("metro_id")[col].transform(
        lambda x: x.shift(1).rolling(window, min_periods=window // 2).mean()
    )


def build_feature_matrix(engine) -> pd.DataFrame:
    """
    Returns a DataFrame with one row per (metro_id, date) and columns:
      target, all features, metro_id, state, date.
    Rows with NaN in any feature column are dropped.
    """
    with Session(engine) as session:
        # ── 1. Price history ──────────────────────────────────────────────
        prices = pd.read_sql(
            text("""
                SELECT p.metro_id, p.date, p.median_price,
                       r.state
                FROM metro_price_history p
                JOIN regions r ON r.metro_id = p.metro_id
                ORDER BY p.metro_id, p.date
            """),
            session.bind,
        )
        prices["date"] = pd.to_datetime(prices["date"])
        prices["median_price"] = prices["median_price"].astype(float)

        # ── 2. National macro indicators ─────────────────────────────────
        macro_national = pd.read_sql(
            text("""
                SELECT date, series_name, value
                FROM macro_indicators
                WHERE geo_id = 'US'
                ORDER BY date
            """),
            session.bind,
        )
        macro_national["date"] = pd.to_datetime(macro_national["date"])
        macro_pivot = (
            macro_national
            .pivot_table(index="date", columns="series_name", values="value", aggfunc="last")
            .reset_index()
        )
        # Forward-fill monthly gaps
        macro_pivot = macro_pivot.sort_values("date").ffill()

        # ── 3. State-level GDP ────────────────────────────────────────────
        gdp = pd.read_sql(
            text("""
                SELECT geo_id AS state, date, value AS gdp_growth
                FROM macro_indicators
                WHERE series_name = 'gdp_growth'
                ORDER BY state, date
            """),
            session.bind,
        )
        gdp["date"] = pd.to_datetime(gdp["date"])
        # BEA is annual — forward-fill within each state
        gdp = gdp.sort_values(["state", "date"])

        # ── 4. Policy flags ───────────────────────────────────────────────
        policy = pd.read_sql(
            text("""
                SELECT state, year,
                       zoning_reform_score,
                       first_time_buyer_credit_active::int AS first_time_buyer_credit_active,
                       state_housing_bond_passed::int AS state_housing_bond_passed,
                       election_year::int AS election_year
                FROM policy_flags
                ORDER BY state, year
            """),
            session.bind,
        )

    # ── 5. Merge everything onto the price history spine ──────────────────
    df = prices.copy()

    # Round macro dates to month start for merge
    macro_pivot["date"] = macro_pivot["date"].dt.to_period("M").dt.to_timestamp()
    df["date_m"] = df["date"].dt.to_period("M").dt.to_timestamp()

    df = df.merge(macro_pivot, left_on="date_m", right_on="date", how="left", suffixes=("", "_macro"))
    if "date_macro" in df.columns:
        df = df.drop(columns=["date_macro"])

    # Merge state GDP (annual, forward-filled per state)
    df["year"] = df["date"].dt.year
    gdp["year"] = gdp["date"].dt.year
    gdp_annual = gdp[["state", "year", "gdp_growth"]].drop_duplicates()
    df = df.merge(gdp_annual, on=["state", "year"], how="left")

    # Merge policy flags (annual per state)
    df = df.merge(policy, on=["state", "year"], how="left")

    df = df.sort_values(["metro_id", "date"]).reset_index(drop=True)

    # ── 6. Price momentum features ─────────────────────────────────────────
    df["price_lag1"]  = _lag(df, "median_price", 1)
    df["price_lag3"]  = _lag(df, "median_price", 3)
    df["price_lag12"] = _lag(df, "median_price", 12)

    df["price_roll3"]  = _rolling(df, "median_price", 3)
    df["price_roll6"]  = _rolling(df, "median_price", 6)
    df["price_roll12"] = _rolling(df, "median_price", 12)

    df["price_mom_3m"]  = (df["median_price"] / df["price_lag3"]  - 1) * 100
    df["price_mom_12m"] = (df["median_price"] / df["price_lag12"] - 1) * 100

    # ── 7. Macro lags (prevent leakage) ────────────────────────────────────
    for col in ["mortgage_rate_30y", "fed_funds_rate", "cpi", "unemployment"]:
        if col in df.columns:
            df[f"{col}_lag1"] = _lag(df, col, 1)
            df = df.drop(columns=[col], errors="ignore")

    if "housing_starts" in df.columns:
        df["housing_starts_lag2"] = _lag(df, "housing_starts", 2)
        df = df.drop(columns=["housing_starts"], errors="ignore")

    if "gdp_growth" in df.columns:
        df["gdp_growth_lag1"] = _lag(df, "gdp_growth", 1)
        df = df.drop(columns=["gdp_growth"], errors="ignore")

    # ── 8. Calendar ──────────────────────────────────────────────────────────
    df["month_of_year"] = df["date"].dt.month

    # ── 9. Fed rate change (monetary policy signal) ────────────────────────
    if "fed_funds_rate_lag1" in df.columns:
        df["fed_rate_change"] = df["fed_funds_rate_lag1"] - _lag(df, "fed_funds_rate_lag1", 1)

    # ── 10. Policy fill defaults ──────────────────────────────────────────────
    for col in ["zoning_reform_score", "first_time_buyer_credit_active",
                "state_housing_bond_passed", "election_year"]:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    # ── 11. Final feature list ────────────────────────────────────────────────
    FEATURES = [
        # Price momentum
        "price_lag1", "price_lag3", "price_lag12",
        "price_roll3", "price_roll6", "price_roll12",
        "price_mom_3m", "price_mom_12m",
        # Macro
        "mortgage_rate_30y_lag1", "fed_funds_rate_lag1", "fed_rate_change",
        "cpi_lag1", "housing_starts_lag2", "unemployment_lag1", "gdp_growth_lag1",
        # Policy
        "zoning_reform_score", "first_time_buyer_credit_active",
        "state_housing_bond_passed", "election_year",
        # Calendar
        "month_of_year",
        # Identity
        "metro_id",
    ]

    TARGET = "median_price"

    existing = [f for f in FEATURES if f in df.columns]
    missing  = [f for f in FEATURES if f not in df.columns]
    if missing:
        print(f"[features] Warning — missing columns (likely no data yet): {missing}")
        for col in missing:
            df[col] = np.nan

    df["metro_id"] = df["metro_id"].astype("category")

    out = df[["metro_id", "state", "date"] + FEATURES + [TARGET]].copy()
    n_before = len(out)
    # Only drop rows where key price features are NaN (allow sparse macro)
    key_cols = ["price_lag1", "price_lag3", TARGET]
    out = out.dropna(subset=key_cols)
    print(f"[features] {n_before} rows → {len(out)} after dropping NaN in key columns")
    return out


FEATURE_COLS = [
    "price_lag1", "price_lag3", "price_lag12",
    "price_roll3", "price_roll6", "price_roll12",
    "price_mom_3m", "price_mom_12m",
    "mortgage_rate_30y_lag1", "fed_funds_rate_lag1", "fed_rate_change",
    "cpi_lag1", "housing_starts_lag2", "unemployment_lag1", "gdp_growth_lag1",
    "zoning_reform_score", "first_time_buyer_credit_active",
    "state_housing_bond_passed", "election_year",
    "month_of_year",
    "metro_id",
]

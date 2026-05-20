"""
Policy flags ingestion.
Quantified policy outcomes per state — updated annually after election cycles.
"""
import pandas as pd
from sqlalchemy.dialects.postgresql import insert

from app.models.policy_flag import PolicyFlag
from etl.db import get_session

# Curated seed data for 2024 — expand annually.
# zoning_reform_score: 0=none, 1=partial (ADU/upzoning), 2=major reform
POLICY_DATA = [
    # State, zoning_score, buyer_credit, housing_bond
    ("AL", 0, False, False),
    ("AK", 0, False, False),
    ("AZ", 1, False, False),
    ("AR", 0, False, False),
    ("CA", 2, True, True),
    ("CO", 2, True, False),
    ("CT", 1, True, False),
    ("DE", 0, False, False),
    ("FL", 0, False, False),
    ("GA", 0, False, False),
    ("HI", 1, True, True),
    ("ID", 0, False, False),
    ("IL", 1, True, False),
    ("IN", 0, False, False),
    ("IA", 0, False, False),
    ("KS", 0, False, False),
    ("KY", 0, False, False),
    ("LA", 0, False, False),
    ("ME", 1, True, False),
    ("MD", 1, True, False),
    ("MA", 2, True, True),
    ("MI", 1, True, False),
    ("MN", 2, True, False),
    ("MS", 0, False, False),
    ("MO", 0, False, False),
    ("MT", 2, False, False),
    ("NE", 0, False, False),
    ("NV", 1, False, False),
    ("NH", 1, False, False),
    ("NJ", 1, True, False),
    ("NM", 1, True, False),
    ("NY", 1, True, False),
    ("NC", 0, False, False),
    ("ND", 0, False, False),
    ("OH", 0, False, False),
    ("OK", 0, False, False),
    ("OR", 2, True, True),
    ("PA", 0, True, False),
    ("RI", 1, True, False),
    ("SC", 0, False, False),
    ("SD", 0, False, False),
    ("TN", 0, False, False),
    ("TX", 0, False, False),
    ("UT", 1, False, False),
    ("VT", 2, True, False),
    ("VA", 1, True, False),
    ("WA", 2, True, True),
    ("WV", 0, False, False),
    ("WI", 0, False, False),
    ("WY", 0, False, False),
]

YEAR = 2024
ELECTION_YEARS = {2020, 2022, 2024}


def load_to_db(year: int = YEAR) -> None:
    session = get_session()
    try:
        batch = [
            {
                "state": state,
                "year": year,
                "zoning_reform_score": zoning,
                "first_time_buyer_credit_active": buyer_credit,
                "state_housing_bond_passed": housing_bond,
                "election_year": year in ELECTION_YEARS,
            }
            for state, zoning, buyer_credit, housing_bond in POLICY_DATA
        ]
        stmt = insert(PolicyFlag).values(batch).on_conflict_do_update(
            constraint="uq_state_year",
            set_={
                "zoning_reform_score": insert(PolicyFlag).excluded.zoning_reform_score,
                "first_time_buyer_credit_active": insert(PolicyFlag).excluded.first_time_buyer_credit_active,
                "state_housing_bond_passed": insert(PolicyFlag).excluded.state_housing_bond_passed,
                "election_year": insert(PolicyFlag).excluded.election_year,
            },
        )
        session.execute(stmt)
        session.commit()
        print(f"Loaded {len(batch)} policy flag rows for {year}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    load_to_db()

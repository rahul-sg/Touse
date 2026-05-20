from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.macro_indicator import MacroIndicator
from app.models.policy_flag import PolicyFlag
from app.models.region import Region


async def get_market_indicators(metro_id: str, db: AsyncSession) -> dict:
    # Resolve state from metro
    region_result = await db.execute(
        select(Region.state).where(Region.metro_id == metro_id).limit(1)
    )
    state = region_result.scalar_one_or_none()

    async def latest(series_name: str, geo_id: str = "US") -> float | None:
        result = await db.execute(
            select(MacroIndicator.value)
            .where(MacroIndicator.series_name == series_name)
            .where(MacroIndicator.geo_id == geo_id)
            .order_by(desc(MacroIndicator.date))
            .limit(1)
        )
        val = result.scalar_one_or_none()
        return float(val) if val is not None else None

    mortgage_rate = await latest("mortgage_rate_30y")
    unemployment = await latest("unemployment")
    cpi = await latest("cpi")
    gdp_growth = await latest("gdp_growth", geo_id=state or "US")

    # Policy notes for the state
    policy_notes = []
    if state:
        policy_result = await db.execute(
            select(PolicyFlag)
            .where(PolicyFlag.state == state)
            .order_by(desc(PolicyFlag.year))
            .limit(1)
        )
        policy = policy_result.scalar_one_or_none()
        if policy:
            if policy.first_time_buyer_credit_active:
                policy_notes.append(f"{state} has an active first-time buyer credit")
            if policy.zoning_reform_score == 2:
                policy_notes.append(f"{state} passed major zoning reform — increased supply expected")
            elif policy.zoning_reform_score == 1:
                policy_notes.append(f"{state} has partial zoning reform (ADU/upzoning)")
            if policy.state_housing_bond_passed:
                policy_notes.append(f"{state} passed a housing bond measure in the last 2 years")
            if policy.election_year:
                policy_notes.append("Election year — policy uncertainty may affect market sentiment")

    return {
        "metro_id": metro_id,
        "mortgage_rate": mortgage_rate,
        "unemployment": unemployment,
        "cpi_yoy": cpi,
        "gdp_growth": gdp_growth,
        "affordability_index": None,  # calculated in Phase 2
        "policy_notes": policy_notes,
    }

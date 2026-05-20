from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.region import Region


async def search_regions(q: str, db: AsyncSession) -> list[dict]:
    term = f"%{q.lower()}%"
    result = await db.execute(
        select(Region)
        .where(
            or_(
                Region.name.ilike(term),
                Region.state.ilike(term),
                Region.state_name.ilike(term),
            )
        )
        .limit(20)
    )
    regions = result.scalars().all()
    return [
        {
            "metro_id": r.metro_id,
            "name": r.name,
            "state": r.state,
            "zip_codes": r.zip_codes or [],
        }
        for r in regions
    ]

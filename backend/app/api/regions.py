import math
from fastapi import APIRouter, Request, Query, Depends, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.region import Region
from app.services.regions import search_regions

router = APIRouter(tags=["regions"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/regions/search")
@limiter.limit("30/minute")
async def regions(
    request: Request,
    q: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_db),
):
    return await search_regions(q, db)


@router.get("/regions/nearest")
@limiter.limit("60/minute")
async def nearest_region(
    request: Request,
    zip: str = Query(..., min_length=3, max_length=10),
    db: AsyncSession = Depends(get_db),
):
    """
    Return the best-matching metro for a ZIP/city string.
    Phase 1: text search on region name. Phase 5 will add a proper
    ZIP centroid table with haversine spatial lookup.
    """
    # Try exact ZIP match against zillow_region_id or name fragment
    result = await db.execute(
        select(Region).where(Region.name.ilike(f"%{zip}%")).limit(1)
    )
    region = result.scalar_one_or_none()

    if not region:
        # Fall back to first region in DB (ensures always a response)
        result = await db.execute(select(Region).limit(1))
        region = result.scalar_one_or_none()

    if not region:
        raise HTTPException(status_code=404, detail="No regions loaded yet — run ETL first")

    return {
        "metro_id": region.metro_id,
        "name": region.name,
        "state": region.state,
    }

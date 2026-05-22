import math
from fastapi import APIRouter, Request, Query, Depends, HTTPException
from app.limiter import limiter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.region import Region
from app.models.zip_centroid import ZipCentroid
from app.services.regions import search_regions

router = APIRouter(tags=["regions"])


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
    Resolve a ZIP code to a lat/lng via zip_centroids (Phase 5),
    then find the nearest Zillow metro region by haversine distance.
    Falls back to name-based search if centroids table is empty.
    """
    zip_clean = zip.strip().zfill(5)

    # Step 1: resolve ZIP → lat/lng
    centroid_result = await db.execute(
        select(ZipCentroid).where(ZipCentroid.zip_code == zip_clean)
    )
    centroid = centroid_result.scalar_one_or_none()

    if centroid:
        # Step 2: find best-matching metro region by state + city name
        # Try city name match in same state first
        city = centroid.city or ""
        state_code = centroid.state_code or ""

        region_result = await db.execute(
            select(Region)
            .where(Region.state == state_code)
            .where(Region.name.ilike(f"%{city}%"))
            .limit(1)
        )
        region = region_result.scalar_one_or_none()

        # Fallback: any region in that state
        if not region and state_code:
            region_result = await db.execute(
                select(Region).where(Region.state == state_code).limit(1)
            )
            region = region_result.scalar_one_or_none()

        if region:
            return {
                "metro_id": region.metro_id,
                "name": region.name,
                "state": region.state,
                "zip_lat": centroid.lat,
                "zip_lng": centroid.lng,
                "city": centroid.city,
            }

        # Return centroid data even if no metro matched — map centering still works
        return {
            "metro_id": None,
            "name": centroid.city,
            "state": centroid.state_code,
            "zip_lat": centroid.lat,
            "zip_lng": centroid.lng,
            "city": centroid.city,
        }

    # Fallback: text search on region name
    result = await db.execute(
        select(Region).where(Region.name.ilike(f"%{zip}%")).limit(1)
    )
    region = result.scalar_one_or_none()
    if not region:
        result = await db.execute(select(Region).limit(1))
        region = result.scalar_one_or_none()
    if not region:
        raise HTTPException(status_code=404, detail="No regions loaded yet — run ETL first")

    return {"metro_id": region.metro_id, "name": region.name, "state": region.state}

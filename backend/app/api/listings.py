from fastapi import APIRouter, Request, Query, Depends
from app.limiter import limiter
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.listings import get_listings

router = APIRouter(tags=["listings"])


@router.get("/listings")
@limiter.limit("30/minute")
async def listings(
    request: Request,
    lat: float = Query(...),
    lng: float = Query(...),
    radius_miles: float = Query(default=10.0),
    max_price: float = Query(...),
    min_beds: int = Query(default=1),
    db: AsyncSession = Depends(get_db),
):
    return await get_listings(lat, lng, radius_miles, max_price, min_beds, db)

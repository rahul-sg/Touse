from fastapi import APIRouter, Request, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.forecast import get_metro_forecast

router = APIRouter(tags=["forecast"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/forecast/{metro_id}")
@limiter.limit("20/minute")
async def forecast(
    request: Request,
    metro_id: str,
    db: AsyncSession = Depends(get_db),
):
    return await get_metro_forecast(metro_id, db)

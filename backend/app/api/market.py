from fastapi import APIRouter, Request, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.services.market import get_market_indicators

router = APIRouter(tags=["market"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/market/{metro_id}")
@limiter.limit("20/minute")
async def market(
    request: Request,
    metro_id: str,
    db: AsyncSession = Depends(get_db),
):
    return await get_market_indicators(metro_id, db)

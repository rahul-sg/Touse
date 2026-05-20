from fastapi import APIRouter, Request, Query, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
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

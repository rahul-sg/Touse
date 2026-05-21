"""
ZIP-level endpoints:
  GET /api/v1/zip/lookup?zip=78701          → lat/lng + city/state
  GET /api/v1/zip/forecast?zip=78701        → price trend indicators
  GET /api/v1/zip/nearest?lat=30.27&lng=-97.74 → nearest ZIP to coordinates
"""
import math
from fastapi import APIRouter, Request, Query, Depends, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta

from app.db import get_db
from app.models.zip_centroid import ZipCentroid
from app.models.zip_price_history import ZipPriceHistory

router = APIRouter(prefix="/api/v1/zip", tags=["zip"])
limiter = Limiter(key_func=get_remote_address)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── ZIP lookup (ZIP → lat/lng) ─────────────────────────────────────────────────

@router.get("/lookup")
@limiter.limit("120/minute")
async def zip_lookup(
    request: Request,
    zip: str = Query(..., min_length=3, max_length=10),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a ZIP code to lat/lng, city, state."""
    zip_clean = zip.strip().zfill(5)
    result = await db.execute(select(ZipCentroid).where(ZipCentroid.zip_code == zip_clean))
    centroid = result.scalar_one_or_none()

    if not centroid:
        raise HTTPException(status_code=404, detail=f"ZIP {zip} not found")

    return {
        "zip_code": centroid.zip_code,
        "lat": centroid.lat,
        "lng": centroid.lng,
        "city": centroid.city,
        "state_code": centroid.state_code,
        "state_name": centroid.state_name,
    }


# ── Nearest ZIP (lat/lng → ZIP) ────────────────────────────────────────────────

@router.get("/nearest")
@limiter.limit("60/minute")
async def nearest_zip(
    request: Request,
    lat: float = Query(...),
    lng: float = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Find the nearest ZIP centroid to a lat/lng coordinate.

    Uses a tight ±0.5° bounding box first (≈55 km, usually 50-200 ZIPs,
    no row limit needed). Falls back to ±1.5° if nothing found in the
    tighter box (sparse rural areas).
    """
    async def _candidates(delta: float):
        result = await db.execute(
            select(ZipCentroid)
            .where(ZipCentroid.lat.between(lat - delta, lat + delta))
            .where(ZipCentroid.lng.between(lng - delta, lng + delta))
        )
        return result.scalars().all()

    candidates = await _candidates(0.5)
    if not candidates:
        candidates = await _candidates(1.5)
    if not candidates:
        raise HTTPException(status_code=404, detail="No ZIP centroids loaded — run ETL first")

    best = min(candidates, key=lambda c: _haversine_km(lat, lng, c.lat, c.lng))
    return {
        "zip_code": best.zip_code,
        "lat": best.lat,
        "lng": best.lng,
        "city": best.city,
        "state_code": best.state_code,
    }


# ── ZIP price trend ────────────────────────────────────────────────────────────

@router.get("/forecast")
@limiter.limit("60/minute")
async def zip_forecast(
    request: Request,
    zip: str = Query(..., min_length=3, max_length=10),
    db: AsyncSession = Depends(get_db),
):
    """Return price trend indicators for a ZIP code from zip_price_history."""
    zip_clean = zip.strip().zfill(5)
    cutoff = date.today() - timedelta(days=365 * 3)  # last 3 years

    result = await db.execute(
        select(ZipPriceHistory)
        .where(ZipPriceHistory.zip_code == zip_clean)
        .where(ZipPriceHistory.date >= cutoff)
        .order_by(ZipPriceHistory.date)
    )
    rows = result.scalars().all()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"No price history for ZIP {zip} — run ETL (etl.zillow_zip) first",
        )

    prices = [(r.date, r.median_value) for r in rows if r.median_value]
    if len(prices) < 4:
        raise HTTPException(status_code=404, detail="Insufficient price history for this ZIP")

    latest_date, latest_price = prices[-1]
    city = rows[-1].city
    state = rows[-1].state
    metro = rows[-1].metro

    def _price_ago(months: int) -> float | None:
        target = latest_date - timedelta(days=months * 30)
        closest = min(prices, key=lambda p: abs((p[0] - target).days))
        if abs((closest[0] - target).days) > 45:
            return None
        return closest[1]

    p3m = _price_ago(3)
    p6m = _price_ago(6)
    p12m = _price_ago(12)

    def _trend(old: float | None) -> float | None:
        if old is None or old == 0:
            return None
        return round((latest_price - old) / old * 100, 2)

    trend_3m = _trend(p3m)
    trend_6m = _trend(p6m)
    trend_12m = _trend(p12m)

    # Simple direction label
    if trend_12m is not None:
        if trend_12m > 5:
            direction = "rising"
        elif trend_12m < -2:
            direction = "falling"
        else:
            direction = "flat"
    else:
        direction = "unknown"

    return {
        "zip_code": zip_clean,
        "city": city,
        "state": state,
        "metro": metro,
        "current_median_value": round(latest_price),
        "as_of": latest_date.isoformat(),
        "trend_3m_pct": trend_3m,
        "trend_6m_pct": trend_6m,
        "trend_12m_pct": trend_12m,
        "direction": direction,
        "data_points": len(prices),
    }

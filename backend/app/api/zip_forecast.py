"""
ZIP-level endpoints:
  GET /api/v1/zip/lookup?zip=78701          → lat/lng + city/state
  GET /api/v1/zip/forecast?zip=78701        → price trend indicators
  GET /api/v1/zip/nearest?lat=30.27&lng=-97.74 → nearest ZIP to coordinates
  GET /api/v1/zip/projection?zip=78701      → 12-month Prophet price forecast
  GET /api/v1/zip/market-context?zip=78701  → national + state economic indicators
"""
import math
from fastapi import APIRouter, Request, Query, Depends, HTTPException
from app.limiter import limiter
from sqlalchemy import select, desc, text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, timedelta

from app.db import get_db
from app.models.zip_centroid import ZipCentroid
from app.models.zip_price_history import ZipPriceHistory
from app.models.macro_indicator import MacroIndicator
from app.models.forecast_realization import ForecastRealization
from app.services.zip_projection import get_or_train

router = APIRouter(prefix="/api/v1/zip", tags=["zip"])


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
        raise HTTPException(status_code=404, detail="No ZIP found near these coordinates.")

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
    home_type: str = Query(default="all", regex="^(all|single_family|condo)$"),
    db: AsyncSession = Depends(get_db),
):
    """Return price trend indicators for a (ZIP, home_type) from zip_price_history."""
    zip_clean = zip.strip().zfill(5)
    cutoff = date.today() - timedelta(days=365 * 3)  # last 3 years

    result = await db.execute(
        select(ZipPriceHistory)
        .where(ZipPriceHistory.zip_code == zip_clean)
        .where(ZipPriceHistory.home_type == home_type)
        .where(ZipPriceHistory.date >= cutoff)
        .order_by(ZipPriceHistory.date)
    )
    rows = result.scalars().all()

    if not rows:
        # Differentiate "this home type has no series here" from "no data at all".
        # If 'all' has data but the requested home_type doesn't, Zillow simply
        # doesn't publish a separate series for that type in this ZIP.
        if home_type != "all":
            any_data = await db.scalar(
                select(ZipPriceHistory.id)
                .where(ZipPriceHistory.zip_code == zip_clean)
                .limit(1)
            )
            if any_data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Zillow doesn't publish a separate {home_type.replace('_', ' ')} price series for ZIP {zip}. Try All homes.",
                )
        raise HTTPException(
            status_code=404,
            detail=f"No price history available for ZIP {zip}.",
        )

    prices = [(r.date, r.median_value) for r in rows if r.median_value]
    if len(prices) < 4:
        raise HTTPException(status_code=404, detail=f"Not enough price history for ZIP {zip} to compute trends.")

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


# ── ZIP Prophet projection (12-month ML forecast) ──────────────────────────────

@router.get("/projection")
@limiter.limit("20/minute")
async def zip_projection(
    request: Request,
    zip: str = Query(..., min_length=3, max_length=10),
    home_type: str = Query(default="all", regex="^(all|single_family|condo)$"),
    db: AsyncSession = Depends(get_db),
):
    """Return a 12-month Prophet price projection for a (ZIP, home_type).

    Trains the model on demand the first time a (ZIP, home_type) is requested
    (a few seconds), then serves the cached result instantly on later requests.
    """
    zip_clean = zip.strip().zfill(5)
    result = await get_or_train(zip_clean, db, home_type=home_type)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Not enough price history to build a projection for ZIP {zip}.",
        )
    return result


# ── National + state market context ────────────────────────────────────────────

async def _latest_macro(
    db: AsyncSession, series_name: str, geo_id: str = "US"
) -> tuple[float | None, date | None]:
    """Return (value, date) for the most recent observation of a macro series."""
    row = (
        await db.execute(
            select(MacroIndicator.value, MacroIndicator.date)
            .where(
                MacroIndicator.series_name == series_name,
                MacroIndicator.geo_id == geo_id,
            )
            .order_by(desc(MacroIndicator.date))
            .limit(1)
        )
    ).first()
    return (float(row[0]), row[1]) if row else (None, None)


@router.get("/market-context")
@limiter.limit("60/minute")
async def market_context(
    request: Request,
    zip: str = Query(..., min_length=3, max_length=10),
    db: AsyncSession = Depends(get_db),
):
    """National + state-level economic indicators relevant to a ZIP's market."""
    zip_clean = zip.strip().zfill(5)

    state_code = await db.scalar(
        select(ZipCentroid.state_code).where(ZipCentroid.zip_code == zip_clean)
    )

    mortgage_rate, mortgage_date = await _latest_macro(db, "mortgage_rate_30y")
    unemployment, _ = await _latest_macro(db, "unemployment")
    fed_funds, _ = await _latest_macro(db, "fed_funds_rate")

    # CPI is stored as the raw index — derive year-over-year inflation.
    latest_cpi, cpi_date = await _latest_macro(db, "cpi")
    cpi_yoy_pct: float | None = None
    if latest_cpi is not None and cpi_date is not None:
        prior = await db.scalar(
            select(MacroIndicator.value)
            .where(
                MacroIndicator.series_name == "cpi",
                MacroIndicator.geo_id == "US",
                MacroIndicator.date <= cpi_date - timedelta(days=350),
            )
            .order_by(desc(MacroIndicator.date))
            .limit(1)
        )
        if prior:
            cpi_yoy_pct = round((latest_cpi - float(prior)) / float(prior) * 100, 1)

    state_gdp_pct, state_gdp_date = (None, None)
    if state_code:
        state_gdp_pct, state_gdp_date = await _latest_macro(db, "gdp_growth", state_code)

    return {
        "zip_code": zip_clean,
        "state_code": state_code,
        "mortgage_rate_30y": round(mortgage_rate, 2) if mortgage_rate is not None else None,
        "mortgage_rate_as_of": mortgage_date.isoformat() if mortgage_date else None,
        "cpi_yoy_pct": cpi_yoy_pct,
        "unemployment_pct": round(unemployment, 1) if unemployment is not None else None,
        "fed_funds_rate": round(fed_funds, 2) if fed_funds is not None else None,
        "state_gdp_growth_pct": round(state_gdp_pct, 1) if state_gdp_pct is not None else None,
        "state_gdp_year": state_gdp_date.year if state_gdp_date else None,
    }


# ── Per-(ZIP, home_type) realized-accuracy track record ────────────────────────

@router.get("/forecast-accuracy")
@limiter.limit("60/minute")
async def zip_forecast_accuracy(
    request: Request,
    zip: str = Query(..., min_length=3, max_length=10),
    home_type: str = Query(default="all", regex="^(all|single_family|condo)$"),
    db: AsyncSession = Depends(get_db),
):
    """Realized accuracy of past served forecasts for a (ZIP, home_type).

    Reads forecast_realizations rows with `actual_price IS NOT NULL` (i.e. the
    12-month horizon arrived and was backfilled) and returns mean absolute
    percentage error plus a signed bias. Lets the forecast page surface a
    live track record — "our forecasts in this ZIP have averaged X% MAPE over
    the last 12 months."

    Returns 200 with `{ samples: 0, ... }` rather than 404 when no realized
    forecasts exist yet — the frontend treats it as "no track record yet" and
    just hides the badge.
    """
    from sqlalchemy import func as _func, desc as _desc

    zip_clean = zip.strip().zfill(5)
    samples = (
        await db.execute(
            select(
                _func.count().label("n"),
                _func.avg(ForecastRealization.abs_pct_error).label("mape"),
                _func.avg(ForecastRealization.signed_pct_error).label("bias"),
                _func.max(ForecastRealization.realized_at).label("last_realized"),
            )
            .where(
                ForecastRealization.zip_code == zip_clean,
                ForecastRealization.home_type == home_type,
                ForecastRealization.actual_price.isnot(None),
            )
        )
    ).one()

    return {
        "zip_code": zip_clean,
        "home_type": home_type,
        "samples": int(samples.n or 0),
        "mape": float(samples.mape) if samples.mape is not None else None,
        "bias": float(samples.bias) if samples.bias is not None else None,
        "last_realized_at": samples.last_realized.isoformat() if samples.last_realized else None,
    }

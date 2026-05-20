import os
from datetime import datetime, timedelta
import httpx
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.models.listing import ListingCache

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "realty-in-us.p.rapidapi.com"
CACHE_TTL_HOURS = 6


async def _fetch_from_rapidapi(
    lat: float, lng: float, radius_miles: float, max_price: float, min_beds: int
) -> list[dict]:
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST,
        "Content-Type": "application/json",
    }
    payload = {
        "limit": 42,
        "offset": 0,
        "postal_code": None,
        "radius": radius_miles,
        "status": ["for_sale"],
        "sold_date_max": None,
        "price_max": int(max_price),
        "beds_min": min_beds,
        "sort": {"direction": "desc", "field": "list_date"},
        "location": {"longitude": lng, "latitude": lat},
    }
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            "https://realty-in-us.p.rapidapi.com/properties/v3/list",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    listings = []
    for prop in data.get("data", {}).get("home_search", {}).get("results", []):
        loc = prop.get("location", {}).get("address", {})
        coord = prop.get("location", {}).get("coordinate", {})
        detail = prop.get("list_price"), prop.get("description", {})
        listings.append({
            "external_id": prop.get("property_id", ""),
            "source": "rapidapi",
            "address": f"{loc.get('line', '')}, {loc.get('city', '')}, {loc.get('state_code', '')} {loc.get('postal_code', '')}",
            "price": float(prop.get("list_price") or 0),
            "beds": detail[1].get("beds"),
            "baths": detail[1].get("baths"),
            "lat": float(coord.get("lat") or lat),
            "lng": float(coord.get("lon") or lng),
            "zip_code": loc.get("postal_code"),
            "listing_url": f"https://www.realtor.com/realestateandhomes-detail/{prop.get('permalink', '')}",
            "fetched_at": datetime.utcnow(),
        })
    return listings


def _mock_listings(lat: float, lng: float, max_price: float, min_beds: int) -> list[dict]:
    """Dev fallback when no RAPIDAPI_KEY is set."""
    import random
    random.seed(int(lat * 100 + lng * 100))
    results = []
    for i in range(12):
        price = random.randint(int(max_price * 0.5), int(max_price))
        beds = random.randint(min_beds, min_beds + 2)
        results.append({
            "id": f"mock-{i}",
            "address": f"{random.randint(100,9999)} Example St, Mock City, US",
            "price": price,
            "beds": beds,
            "baths": random.choice([1.0, 1.5, 2.0, 2.5, 3.0]),
            "lat": lat + random.uniform(-0.05, 0.05),
            "lng": lng + random.uniform(-0.05, 0.05),
            "listing_url": "#",
        })
    return results


async def _upsert_cache(db: AsyncSession, listings: list[dict]) -> None:
    if not listings:
        return
    stmt = insert(ListingCache).values(listings).on_conflict_do_update(
        constraint="uq_listing_source",
        set_={
            "price": insert(ListingCache).excluded.price,
            "fetched_at": insert(ListingCache).excluded.fetched_at,
        },
    )
    await db.execute(stmt)
    await db.commit()


async def get_listings(
    lat: float,
    lng: float,
    radius_miles: float,
    max_price: float,
    min_beds: int,
    db: AsyncSession,
) -> list[dict]:
    if not RAPIDAPI_KEY:
        return _mock_listings(lat, lng, max_price, min_beds)

    # Check cache freshness
    stale_cutoff = datetime.utcnow() - timedelta(hours=CACHE_TTL_HOURS)
    result = await db.execute(
        select(ListingCache)
        .where(
            and_(
                ListingCache.price <= max_price,
                ListingCache.beds >= min_beds,
                ListingCache.fetched_at >= stale_cutoff,
            )
        )
        .limit(42)
    )
    cached = result.scalars().all()

    if cached:
        return [
            {
                "id": str(c.id),
                "address": c.address,
                "price": float(c.price),
                "beds": c.beds,
                "baths": float(c.baths) if c.baths else None,
                "lat": float(c.lat),
                "lng": float(c.lng),
                "listing_url": c.listing_url,
            }
            for c in cached
        ]

    # Fetch fresh from API
    raw = await _fetch_from_rapidapi(lat, lng, radius_miles, max_price, min_beds)
    await _upsert_cache(db, raw)
    return [
        {
            "id": r["external_id"],
            "address": r["address"],
            "price": r["price"],
            "beds": r["beds"],
            "baths": r["baths"],
            "lat": r["lat"],
            "lng": r["lng"],
            "listing_url": r["listing_url"],
        }
        for r in raw
    ]

import os
from datetime import datetime, timedelta
import httpx
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.models.listing import ListingCache
from app.services.geocoding import geocode_many

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
RAPIDAPI_HOST = "realty-us.p.rapidapi.com"
CACHE_TTL_HOURS = 6


def _bbox_polygon(lat: float, lng: float, radius_miles: float) -> list[list[float]]:
    """Convert a center point + radius into a closed bounding box polygon [lng, lat]."""
    import math
    lat_delta = radius_miles / 69.0
    lng_delta = radius_miles / (69.0 * math.cos(math.radians(lat)))
    n, s = lat + lat_delta, lat - lat_delta
    e, w = lng + lng_delta, lng - lng_delta
    # Closed polygon: 5 points, GeoJSON order [lng, lat]
    return [[w, n], [e, n], [e, s], [w, s], [w, n]]


async def _fetch_from_rapidapi(
    lat: float, lng: float, radius_miles: float, max_price: float, min_beds: int
) -> list[dict]:
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST,
        "Content-Type": "application/json",
    }
    payload = {"coordinates": _bbox_polygon(lat, lng, radius_miles)}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"https://{RAPIDAPI_HOST}/properties/coords/search-buy",
            headers=headers,
            params={"sortBy": "relevance"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    # Response: {"data": {"count": N, "total": N, "results": [...]}, ...}
    results = (data.get("data") or {}).get("results") or []
    listings = []
    for prop in results:
        loc = prop.get("location", {})
        address = loc.get("address", {})
        coord = loc.get("coordinate", {})
        desc = prop.get("description", {})
        price = prop.get("list_price") or 0
        photo = (prop.get("primary_photo") or {}).get("href", "")

        raw_lat = coord.get("lat")
        raw_lng = coord.get("lon")

        line = address.get("line", "")
        city = address.get("city", "")
        state = address.get("state_code", "")
        zipcode = address.get("postal_code", "")
        full_address = f"{line}, {city}, {state} {zipcode}".strip(", ")

        listings.append({
            "external_id": str(prop.get("property_id") or ""),
            "source": "rapidapi",
            "address": full_address,
            "price": float(price),
            "beds": desc.get("beds"),
            "baths": desc.get("baths_consolidated") or desc.get("baths"),
            "lat": float(raw_lat) if raw_lat is not None else None,
            "lng": float(raw_lng) if raw_lng is not None else None,
            "zip_code": zipcode,
            "listing_url": prop.get("href") or f"https://www.realtor.com/realestateandhomes-detail/{prop.get('property_id','')}",
            "photo_url": photo,
            "fetched_at": datetime.utcnow(),
        })

    # The listings API often omits per-property coordinates. Geocode those
    # addresses via the US Census geocoder so each pin lands at its true
    # location. Fall back to the ZIP center only when geocoding also fails.
    missing = [l for l in listings if l["lat"] is None or l["lng"] is None]
    if missing:
        geocoded = await geocode_many([l["address"] for l in missing])
        for listing, result in zip(missing, geocoded):
            if result is not None:
                listing["lat"], listing["lng"] = result
            else:
                listing["lat"], listing["lng"] = lat, lng

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

    # Bounding box for cache lookup (~radius_miles converted to degrees)
    import math as _math
    lat_delta = radius_miles / 69.0
    lng_delta = radius_miles / (69.0 * _math.cos(_math.radians(lat)))

    # Check cache freshness — must also be geographically nearby
    stale_cutoff = datetime.utcnow() - timedelta(hours=CACHE_TTL_HOURS)
    result = await db.execute(
        select(ListingCache)
        .where(
            and_(
                ListingCache.price <= max_price,
                # Include listings with unknown bed count (NULL) — better to show and let user judge
                or_(ListingCache.beds.is_(None), ListingCache.beds >= min_beds),
                ListingCache.fetched_at >= stale_cutoff,
                ListingCache.lat.between(lat - lat_delta, lat + lat_delta),
                ListingCache.lng.between(lng - lng_delta, lng + lng_delta),
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
                "photo_url": getattr(c, "photo_url", None),
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
            "photo_url": r.get("photo_url"),
        }
        for r in raw
    ]

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
CACHE_RESULT_LIMIT = 42

# Canonical property types our filters speak (matches the frontend chip set).
_PROPERTY_TYPE_MAP = {
    "single_family": "single_family",
    "single_family_residence": "single_family",
    "single family": "single_family",
    "sfr": "single_family",
    "condo": "condo",
    "condos": "condo",
    "condominium": "condo",
    "co_op": "condo",
    "coop": "condo",
    "townhome": "townhouse",
    "townhomes": "townhouse",
    "townhouse": "townhouse",
    "townhouses": "townhouse",
    "multi_family": "multi_family",
    "multi-family": "multi_family",
    "duplex_triplex": "multi_family",
    "mobile": "mobile",
    "manufactured": "mobile",
    "mobile_home": "mobile",
    "land": "land",
    "lot": "land",
    "farm": "land",
}


def _normalize_property_type(raw) -> str | None:
    """Normalize RapidAPI's varied property-type strings to a small canonical set."""
    if not raw:
        return None
    key = str(raw).strip().lower()
    return _PROPERTY_TYPE_MAP.get(key, key)  # unknown → store as-is rather than drop


def _coerce_int(v) -> int | None:
    try:
        return int(v) if v is not None else None
    except (TypeError, ValueError):
        return None


def _bbox_polygon(lat: float, lng: float, radius_miles: float) -> list[list[float]]:
    """Convert a center point + radius into a closed bounding box polygon [lng, lat]."""
    import math
    lat_delta = radius_miles / 69.0
    lng_delta = radius_miles / (69.0 * math.cos(math.radians(lat)))
    n, s = lat + lat_delta, lat - lat_delta
    e, w = lng + lng_delta, lng - lng_delta
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

    results = (data.get("data") or {}).get("results") or []
    listings: list[dict] = []
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
            "property_type": _normalize_property_type(desc.get("type")),
            "sqft": _coerce_int(desc.get("sqft")),
            "lot_sqft": _coerce_int(desc.get("lot_sqft")),
            "year_built": _coerce_int(desc.get("year_built")),
            "fetched_at": datetime.utcnow(),
        })

    # Geocode addresses missing coordinates so each pin lands at its true location.
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
    types = ["single_family", "condo", "townhouse"]
    out = []
    for i in range(12):
        price = random.randint(int(max_price * 0.5), int(max_price))
        out.append({
            "id": f"mock-{i}",
            "address": f"{random.randint(100,9999)} Example St, Mock City, US",
            "price": price,
            "beds": random.randint(min_beds, min_beds + 2),
            "baths": random.choice([1.0, 1.5, 2.0, 2.5, 3.0]),
            "lat": lat + random.uniform(-0.05, 0.05),
            "lng": lng + random.uniform(-0.05, 0.05),
            "listing_url": "#",
            "property_type": random.choice(types),
            "sqft": random.choice([900, 1200, 1500, 1800, 2200, 2800]),
            "lot_sqft": random.choice([None, 3000, 5500, 8000]),
            "year_built": random.choice([1965, 1985, 1998, 2005, 2015]),
        })
    return out


async def _upsert_cache(db: AsyncSession, listings: list[dict]) -> None:
    if not listings:
        return
    refresh_cols = (
        "price", "fetched_at",
        "property_type", "sqft", "lot_sqft", "year_built",
    )
    stmt = insert(ListingCache).values(listings).on_conflict_do_update(
        constraint="uq_listing_source",
        set_={c: insert(ListingCache).excluded[c] for c in refresh_cols},
    )
    await db.execute(stmt)
    await db.commit()


def _serialize_cached(c: ListingCache) -> dict:
    return {
        "id": str(c.id),
        "address": c.address,
        "price": float(c.price),
        "beds": c.beds,
        "baths": float(c.baths) if c.baths else None,
        "lat": float(c.lat),
        "lng": float(c.lng),
        "listing_url": c.listing_url,
        "photo_url": c.photo_url,
        "property_type": c.property_type,
        "sqft": c.sqft,
        "lot_sqft": c.lot_sqft,
        "year_built": c.year_built,
    }


def _matches_filters(
    r: dict,
    max_price: float,
    min_beds: int,
    property_types: list[str] | None,
    min_sqft: int | None,
    min_year_built: int | None,
) -> bool:
    """Apply user filters to a freshly-fetched listing dict (cache path filters in SQL)."""
    if r["price"] > max_price:
        return False
    if r["beds"] is not None and r["beds"] < min_beds:
        return False
    if property_types and r.get("property_type") not in property_types:
        return False
    if min_sqft is not None and r.get("sqft") is not None and r["sqft"] < min_sqft:
        return False
    if min_year_built is not None and r.get("year_built") is not None and r["year_built"] < min_year_built:
        return False
    return True


async def get_listings(
    lat: float,
    lng: float,
    radius_miles: float,
    max_price: float,
    min_beds: int,
    db: AsyncSession,
    property_types: list[str] | None = None,
    min_sqft: int | None = None,
    min_year_built: int | None = None,
) -> list[dict]:
    if not RAPIDAPI_KEY:
        # Apply the same filters to mock data so the UI behaves identically.
        raw = _mock_listings(lat, lng, max_price, min_beds)
        return [r for r in raw if _matches_filters(r, max_price, min_beds, property_types, min_sqft, min_year_built)]

    import math as _math
    lat_delta = radius_miles / 69.0
    lng_delta = radius_miles / (69.0 * _math.cos(_math.radians(lat)))

    stale_cutoff = datetime.utcnow() - timedelta(hours=CACHE_TTL_HOURS)
    filters = [
        ListingCache.price <= max_price,
        # Listings with unknown bed count stay in — better to show than hide.
        or_(ListingCache.beds.is_(None), ListingCache.beds >= min_beds),
        ListingCache.fetched_at >= stale_cutoff,
        ListingCache.lat.between(lat - lat_delta, lat + lat_delta),
        ListingCache.lng.between(lng - lng_delta, lng + lng_delta),
    ]
    if property_types:
        # Strict — if the user filters to "condo only" we exclude unknown types.
        filters.append(ListingCache.property_type.in_(property_types))
    if min_sqft is not None:
        filters.append(or_(ListingCache.sqft.is_(None), ListingCache.sqft >= min_sqft))
    if min_year_built is not None:
        filters.append(or_(ListingCache.year_built.is_(None), ListingCache.year_built >= min_year_built))

    result = await db.execute(
        select(ListingCache).where(and_(*filters)).limit(CACHE_RESULT_LIMIT)
    )
    cached = result.scalars().all()
    if cached:
        return [_serialize_cached(c) for c in cached]

    # Cache miss → fetch fresh + upsert, then apply user filters.
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
            "property_type": r.get("property_type"),
            "sqft": r.get("sqft"),
            "lot_sqft": r.get("lot_sqft"),
            "year_built": r.get("year_built"),
        }
        for r in raw
        if _matches_filters(r, max_price, min_beds, property_types, min_sqft, min_year_built)
    ]

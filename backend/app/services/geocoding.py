"""
US Census Bureau geocoder — free, no API key required, US-only.

Turns a street address into (lat, lng). Used to give map listings their true
location when the listings API returns no per-property coordinates.
https://geocoding.geo.census.gov/geocoder/
"""
import asyncio
import httpx

CENSUS_ONELINE = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
_BENCHMARK = "Public_AR_Current"


async def geocode_oneline(
    client: httpx.AsyncClient, address: str
) -> tuple[float, float] | None:
    """Return (lat, lng) for a one-line US address, or None if there is no match."""
    if not address or not address.strip():
        return None
    try:
        resp = await client.get(
            CENSUS_ONELINE,
            params={"address": address, "benchmark": _BENCHMARK, "format": "json"},
            timeout=10,
        )
        resp.raise_for_status()
        matches = resp.json().get("result", {}).get("addressMatches", [])
        if not matches:
            return None
        coords = matches[0]["coordinates"]
        return float(coords["y"]), float(coords["x"])  # y = latitude, x = longitude
    except (httpx.HTTPError, KeyError, ValueError, IndexError):
        return None


async def geocode_many(addresses: list[str]) -> list[tuple[float, float] | None]:
    """Geocode a list of addresses concurrently. Returns results in input order."""
    if not addresses:
        return []
    # Cap concurrency so we stay polite to the free Census service.
    sem = asyncio.Semaphore(8)
    async with httpx.AsyncClient() as client:
        async def _one(addr: str) -> tuple[float, float] | None:
            async with sem:
                return await geocode_oneline(client, addr)

        return await asyncio.gather(*(_one(a) for a in addresses))

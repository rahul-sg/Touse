"""
Backfill real coordinates for cached listings using the US Census geocoder.

Many cached listings were stored with lat/lng set to the ZIP centroid because
the listings API returned no per-property coordinates — so every pin stacked at
one point on the map. This re-geocodes them from their street address so each
pin lands at its true location.

Run:  python3 -m etl.geocode_listings
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from etl.db import get_session
from app.models.listing import ListingCache
from app.services.geocoding import geocode_many


def run() -> None:
    session = get_session()
    try:
        rows = session.execute(select(ListingCache)).scalars().all()
        if not rows:
            print("No cached listings to geocode.")
            return

        print(f"Geocoding {len(rows)} cached listings via US Census geocoder...")
        results = asyncio.run(geocode_many([r.address for r in rows]))

        updated = 0
        for row, result in zip(rows, results):
            if result is not None:
                row.lat, row.lng = result
                updated += 1
        session.commit()
        print(f"Updated {updated}/{len(rows)} listings with real coordinates.")
        if updated < len(rows):
            print(f"  {len(rows) - updated} could not be matched — left at their existing location.")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run()

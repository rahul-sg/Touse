"""
ZIP centroid seeder.

Uses pgeocode (backed by GeoNames dataset) to seed the zip_centroids table
with lat/lng for every US ZIP code. Run once; subsequent runs are idempotent.

Usage:
    DATABASE_URL=postgresql+asyncpg://... python3 -m etl.zip_centroids
"""
import pgeocode
import pandas as pd
from sqlalchemy import text
from etl.db import get_session

BATCH_SIZE = 500


def seed_zip_centroids() -> None:
    print("Fetching ZIP centroids from GeoNames via pgeocode…")
    nomi = pgeocode.Nominatim("us")

    df: pd.DataFrame = nomi._data.copy()
    df = df.rename(columns={
        "postal_code": "zip_code",
        "latitude": "lat",
        "longitude": "lng",
        "place_name": "city",
        "state_name": "state_name",
        "state_code": "state_code",
        "county_name": "county",
    })

    keep = ["zip_code", "lat", "lng", "city", "state_name", "state_code", "county"]
    df = df[[c for c in keep if c in df.columns]].dropna(subset=["lat", "lng"])
    df["zip_code"] = df["zip_code"].astype(str).str.zfill(5)

    total = len(df)
    print(f"Seeding {total:,} ZIP centroids in batches of {BATCH_SIZE}…")

    session = get_session()
    try:
        session.execute(text("TRUNCATE TABLE zip_centroids"))
        session.commit()

        for i in range(0, total, BATCH_SIZE):
            batch = df.iloc[i : i + BATCH_SIZE]
            rows = []
            for _, row in batch.iterrows():
                rows.append({
                    "zip_code": str(row["zip_code"]),
                    "lat": float(row["lat"]),
                    "lng": float(row["lng"]),
                    "city": str(row["city"]) if pd.notna(row.get("city")) else None,
                    "state_name": str(row["state_name"]) if pd.notna(row.get("state_name")) else None,
                    "state_code": str(row["state_code"]) if pd.notna(row.get("state_code")) else None,
                    "county": str(row["county"]) if pd.notna(row.get("county")) else None,
                })

            session.execute(
                text(
                    "INSERT INTO zip_centroids "
                    "(zip_code, lat, lng, city, state_name, state_code, county) "
                    "VALUES (:zip_code, :lat, :lng, :city, :state_name, :state_code, :county) "
                    "ON CONFLICT (zip_code) DO NOTHING"
                ),
                rows,
            )
            session.commit()

            if (i // BATCH_SIZE) % 10 == 0:
                pct = min(100, round((i + BATCH_SIZE) / total * 100))
                print(f"  {pct}% ({i + BATCH_SIZE:,}/{total:,})")

        print(f"Done — {total:,} ZIP centroids loaded.")
    finally:
        session.close()


if __name__ == "__main__":
    seed_zip_centroids()

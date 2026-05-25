from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.limiter import limiter
from app.api import affordability, listings, regions
from app.api import auth
from app.api import scenarios, rental, readiness, compare, zip_forecast, contact, methodology
from app.models.macro_indicator import MacroIndicator
from app.models.zip_price_history import ZipPriceHistory

app = FastAPI(title="Touse API", version="0.1.0")

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "https://touse.app",
    "https://www.touse.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(affordability.router, prefix="/api/v1")
app.include_router(listings.router, prefix="/api/v1")
app.include_router(regions.router, prefix="/api/v1")
app.include_router(auth.router)
app.include_router(scenarios.router)
app.include_router(rental.router)
app.include_router(readiness.router)
app.include_router(compare.router)
# Metro-level forecasting was retired in favour of the ZIP-native pipeline
# (zip_forecast.router → /api/v1/zip/projection, trained on zip_price_history).
app.include_router(zip_forecast.router)
app.include_router(contact.router, prefix="/api/v1")
app.include_router(methodology.router)


@app.get("/health")
async def health():
    """Liveness probe — cheap, no DB. Use for load balancer health checks."""
    return {"status": "ok"}


@app.get("/healthz")
async def healthz(db: AsyncSession = Depends(get_db)):
    """Readiness probe — DB reachability + freshness of key data sources.

    Returns 200 if the API can serve real requests; the JSON body reports
    the most recent observation date per critical data source so a stale
    feed shows up in monitoring before users notice missing forecasts.
    """
    checks: dict[str, str | None] = {}
    status = "ok"

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:  # pragma: no cover — fault-only path
        checks["database"] = f"error: {exc.__class__.__name__}"
        return {"status": "error", "checks": checks}

    # Freshness signals — most recent observation in each table that drives
    # user-facing numbers. Missing means the ETL hasn't ever run for it.
    latest_price = await db.scalar(select(func.max(ZipPriceHistory.date)))
    latest_rate = await db.scalar(
        select(func.max(MacroIndicator.date)).where(
            MacroIndicator.series_name == "mortgage_rate_30y"
        )
    )
    checks["latest_zip_price_month"] = latest_price.isoformat() if latest_price else None
    checks["latest_mortgage_rate"] = latest_rate.isoformat() if latest_rate else None

    if not latest_price or not latest_rate:
        status = "degraded"

    return {"status": status, "checks": checks}

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.api import affordability, listings, regions
from app.api import auth
from app.api import scenarios, rental, readiness, compare, zip_forecast

limiter = Limiter(key_func=get_remote_address)

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


@app.get("/health")
async def health():
    return {"status": "ok"}

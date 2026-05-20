import os
from tasks.celery_app import app

_DB_URL = lambda: os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://touse:touse@localhost:5432/touse",
).replace("postgresql+asyncpg://", "postgresql+psycopg2://")


@app.task(name="tasks.ml_tasks.retrain_prophet_all", bind=True, max_retries=2)
def retrain_prophet_all(self):
    """Retrain Prophet forecast for every metro with enough price history."""
    try:
        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import Session
        from app.models.region import Region
        from app.ml.train_prophet import train_metro

        engine = create_engine(_DB_URL())
        with Session(engine) as session:
            metro_ids = session.execute(select(Region.metro_id)).scalars().all()
            trained = sum(train_metro(session, m) for m in metro_ids)
            print(f"retrain_prophet_all: trained {trained}/{len(metro_ids)} metros")
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * 30)


@app.task(name="tasks.ml_tasks.retrain_prophet_metro", bind=True, max_retries=3)
def retrain_prophet_metro(self, metro_id: str):
    """Retrain Prophet forecast for a single metro (on-demand)."""
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from app.ml.train_prophet import train_metro

        engine = create_engine(_DB_URL())
        with Session(engine) as session:
            train_metro(session, metro_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * 5)


@app.task(name="tasks.ml_tasks.retrain_lightgbm", bind=True, max_retries=2)
def retrain_lightgbm(self):
    """
    Retrain the global LightGBM model across all metros.
    Runs after Prophet (17th of each month) so price history is already fresh.
    """
    try:
        from app.ml.train_lightgbm import run
        run()
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60 * 30)

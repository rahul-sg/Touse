"""Synchronous DB helpers for ETL scripts (Celery runs in sync context)."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://touse:touse@localhost:5432/touse",
).replace("postgresql+asyncpg://", "postgresql+psycopg2://")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)


def get_session() -> Session:
    return SessionLocal()

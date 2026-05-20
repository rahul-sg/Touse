import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://touse:touse@localhost:5432/touse",
)

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session

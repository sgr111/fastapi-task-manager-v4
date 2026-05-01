from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


def get_database_url() -> str:
    """Fix Railway's postgres:// URL to work with asyncpg."""
    url = settings.DATABASE_URL
    url = url.replace("postgres://", "postgresql+asyncpg://")
    url = url.replace("postgresql://", "postgresql+asyncpg://")
    return url


# Async engine — works with asyncpg (PostgreSQL)
engine = create_async_engine(
    get_database_url(),
    echo=settings.DEBUG,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


class Base(DeclarativeBase):
    pass


# Async dependency — used in route handlers via FastAPI's Depends()
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
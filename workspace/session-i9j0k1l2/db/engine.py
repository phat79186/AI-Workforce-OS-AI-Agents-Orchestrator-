"""Async SQLAlchemy engine with connection pool configuration."""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool

_engine: AsyncEngine | None = None


def get_engine(
    database_url: str = "sqlite+aiosqlite:///./app.db",
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_timeout: int = 30,
) -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            database_url,
            poolclass=AsyncAdaptedQueuePool,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_pre_ping=True,
            echo=False,
        )
    return _engine


async def dispose_engine() -> None:
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None

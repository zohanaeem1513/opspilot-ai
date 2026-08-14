from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


class DatabaseNotConfiguredError(RuntimeError):
    """Raised when database access is attempted but DATABASE_URL is not set."""


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        if not settings.database_url:
            raise DatabaseNotConfiguredError("DATABASE_URL is not set")
        _engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        yield session


async def ping_database() -> None:
    """Raises if the database is unreachable or DATABASE_URL is unset."""
    engine = get_engine()
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))

"""Async PostgreSQL engine lifecycle (port of database/postgres/connector.go)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import URL
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config.settings import PostgresSettings


def postgres_url(settings: PostgresSettings) -> URL:
    return URL.create(
        "postgresql+asyncpg",
        username=settings.user,
        password=settings.password.get_secret_value(),
        host=settings.host,
        port=settings.port,
        database=settings.db,
    )


@asynccontextmanager
async def postgres_session_factory(
    settings: PostgresSettings,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """One connection pool for the whole process, closed on exit."""
    engine = create_async_engine(postgres_url(settings), pool_pre_ping=True)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()

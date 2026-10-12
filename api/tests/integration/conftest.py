"""Real PostgreSQL fixtures; the whole package is skipped unless TEST_DATABASE_URL is set."""

import os
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.interface.repositories.postgres.orm import Base

DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if DATABASE_URL:
        return
    skip = pytest.mark.skip(reason="TEST_DATABASE_URL is not set")
    for item in items:
        if "integration" in item.path.parts:
            item.add_marker(skip)


@pytest.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    assert DATABASE_URL
    # The schema is dropped below: refuse to touch anything but a dedicated test database.
    assert make_url(DATABASE_URL).database == "app_test"
    # Function-scoped engine without a pool: asyncpg connections never cross event loops.
    engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()

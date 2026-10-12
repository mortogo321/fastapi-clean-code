import asyncio
import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.entities.user import UserEntity, UserRegisterRequest, UserTokenEntity
from app.domain.errors import EmailAlreadyRegisteredError
from app.interface.repositories.postgres.orm import UserPermissionTable, UserTokenTable
from app.interface.repositories.postgres.user import PostgresUserRepository

Factory = async_sessionmaker[AsyncSession]


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def request(email: str = "ada@example.com") -> UserRegisterRequest:
    return UserRegisterRequest.model_validate(
        {"email": email, "password": "password123", "first_name": "Ada", "last_name": "L"}
    )


def tokens(name: str) -> UserTokenEntity:
    return UserTokenEntity(access=f"access-{name}", refresh=f"refresh-{name}")


def in_one_hour() -> datetime:
    return datetime.now(UTC) + timedelta(hours=1)


def an_hour_ago() -> datetime:
    return datetime.now(UTC) - timedelta(hours=1)


@pytest.fixture
def repo(session_factory: Factory) -> PostgresUserRepository:
    return PostgresUserRepository(session_factory)


async def make_user(repo: PostgresUserRepository, email: str = "ada@example.com") -> UserEntity:
    return await repo.insert_user(request(email), "$2b$04$" + "a" * 53)


async def session_rows(
    session_factory: Factory, user_id: int | None = None
) -> list[UserTokenTable]:
    statement = select(UserTokenTable).order_by(UserTokenTable.id)
    if user_id is not None:
        statement = statement.where(UserTokenTable.user_id == user_id)
    async with session_factory() as session:
        return list((await session.scalars(statement)).all())


async def test_insert_and_get_user(repo: PostgresUserRepository) -> None:
    user = await make_user(repo)
    stored = await repo.get_user_by_email("ada@example.com")
    assert stored is not None
    assert stored.id == user.id
    assert stored.password_hash.startswith("$2b$")
    assert await repo.get_user_by_email("nobody@example.com") is None


async def test_duplicate_email(repo: PostgresUserRepository) -> None:
    await make_user(repo)
    with pytest.raises(EmailAlreadyRegisteredError):
        await make_user(repo)


async def test_only_hashes_are_stored(
    repo: PostgresUserRepository, session_factory: Factory
) -> None:
    user = await make_user(repo)
    token = tokens("one")
    await repo.insert_oauth(user.id, token, in_one_hour())
    (row,) = await session_rows(session_factory)
    assert row.access_token_hash == sha256(token.access)
    assert row.refresh_token_hash == sha256(token.refresh)
    assert token.access not in (row.access_token_hash, row.refresh_token_hash)
    assert token.refresh not in (row.access_token_hash, row.refresh_token_hash)


async def test_insert_oauth_prunes_only_that_users_expired_sessions(
    repo: PostgresUserRepository, session_factory: Factory
) -> None:
    ada = await make_user(repo)
    bob = await make_user(repo, "bob@example.com")
    await repo.insert_oauth(ada.id, tokens("ada-live"), in_one_hour())
    # Expired rows are planted directly: insert_oauth itself would prune them.
    async with session_factory.begin() as session:
        for owner, name in ((ada.id, "ada-old"), (bob.id, "bob-old")):
            session.add(
                UserTokenTable(
                    user_id=owner,
                    access_token_hash=sha256(f"access-{name}"),
                    refresh_token_hash=sha256(f"refresh-{name}"),
                    expires_at=an_hour_ago(),
                )
            )
    assert len(await session_rows(session_factory, ada.id)) == 2

    await repo.insert_oauth(ada.id, tokens("ada-new"), in_one_hour())

    ada_hashes = {row.access_token_hash for row in await session_rows(session_factory, ada.id)}
    assert ada_hashes == {sha256("access-ada-live"), sha256("access-ada-new")}
    bob_hashes = {row.access_token_hash for row in await session_rows(session_factory, bob.id)}
    assert bob_hashes == {sha256("access-bob-old")}


async def test_rotate_oauth(repo: PostgresUserRepository) -> None:
    user = await make_user(repo)
    old, new = tokens("old"), tokens("new")
    await repo.insert_oauth(user.id, old, in_one_hour())

    rotated = await repo.rotate_oauth(user.id, old.refresh, new)
    assert rotated is not None
    assert rotated.id == user.id

    assert await repo.get_user_by_access_token(user.id, old.access) is None
    assert await repo.get_user_by_access_token(user.id, new.access) is not None
    assert await repo.rotate_oauth(user.id, old.refresh, tokens("again")) is None


async def test_rotate_requires_matching_user(repo: PostgresUserRepository) -> None:
    ada = await make_user(repo)
    bob = await make_user(repo, "bob@example.com")
    token = tokens("ada")
    await repo.insert_oauth(ada.id, token, in_one_hour())
    assert await repo.rotate_oauth(bob.id, token.refresh, tokens("x")) is None
    assert await repo.get_user_by_access_token(ada.id, token.access) is not None


async def test_concurrent_rotation_has_exactly_one_winner(repo: PostgresUserRepository) -> None:
    user = await make_user(repo)
    old = tokens("old")
    await repo.insert_oauth(user.id, old, in_one_hour())

    results = await asyncio.gather(
        *(repo.rotate_oauth(user.id, old.refresh, tokens(f"new-{i}")) for i in range(2))
    )

    assert sum(result is not None for result in results) == 1


async def test_expired_session_fails_rotation_and_authentication(
    repo: PostgresUserRepository,
) -> None:
    user = await make_user(repo)
    token = tokens("expired")
    await repo.insert_oauth(user.id, token, an_hour_ago())
    assert await repo.rotate_oauth(user.id, token.refresh, tokens("new")) is None
    assert await repo.get_user_by_access_token(user.id, token.access) is None


async def test_get_user_by_access_token_is_scoped_to_user(repo: PostgresUserRepository) -> None:
    ada = await make_user(repo)
    bob = await make_user(repo, "bob@example.com")
    token = tokens("ada")
    await repo.insert_oauth(ada.id, token, in_one_hour())
    assert (await repo.get_user_by_access_token(ada.id, token.access)) is not None
    assert await repo.get_user_by_access_token(bob.id, token.access) is None
    assert await repo.get_user_by_access_token(ada.id, "access-unknown") is None


async def test_delete_oauth(repo: PostgresUserRepository) -> None:
    user = await make_user(repo)
    token = tokens("one")
    await repo.insert_oauth(user.id, token, in_one_hour())
    assert await repo.delete_oauth(user.id, token.refresh) is True
    assert await repo.delete_oauth(user.id, token.refresh) is False
    assert await repo.get_user_by_access_token(user.id, token.access) is None


async def test_permission_lookup(repo: PostgresUserRepository, session_factory: Factory) -> None:
    user = await make_user(repo)
    assert await repo.get_user_permission_by_user_id(user.id) is None
    async with session_factory.begin() as session:
        session.add(UserPermissionTable(user_id=user.id, permission="admin"))
    permission = await repo.get_user_permission_by_user_id(user.id)
    assert permission is not None
    assert (permission.user_id, permission.permission) == (user.id, "admin")

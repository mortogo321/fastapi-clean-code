from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.entities.user import UserRegisterRequest, UserTokenEntity
from app.domain.models.user import UserModel, UserPermissionModel, UserTokenModel
from app.interface.repositories.postgres.crud import PostgresCRUDRepository
from app.interface.repositories.postgres.orm import UserPermissionTable
from app.interface.repositories.postgres.user import PostgresUserRepository

Factory = async_sessionmaker[AsyncSession]


async def add_users(session_factory: Factory, count: int) -> list[int]:
    repo = PostgresUserRepository(session_factory)
    ids = []
    for i in range(count):
        request = UserRegisterRequest.model_validate(
            {
                "email": f"user{i}@example.com",
                "password": "password123",
                "first_name": "U",
                "last_name": str(i),
            }
        )
        ids.append((await repo.insert_user(request, "$2b$04$" + "a" * 53)).id)
    return ids


async def test_users_never_include_password_hash(session_factory: Factory) -> None:
    (user_id,) = await add_users(session_factory, 1)
    repo = PostgresCRUDRepository(session_factory, UserModel)
    one = await repo.get_one_by_id(str(user_id), owner_id=None)
    assert one is not None
    assert "password_hash" not in one.data
    assert set(one.data) == {
        "id",
        "email",
        "first_name",
        "last_name",
        "created_at",
        "updated_at",
    }
    listing = await repo.get_list(1, 10, owner_id=None)
    assert all("password_hash" not in row for row in listing.data)
    assert "password_hash" not in str(listing.data_schema)
    assert "password_hash" not in str(repo.describe_data_source())


async def test_owner_scoping(session_factory: Factory) -> None:
    ada, bob = await add_users(session_factory, 2)
    repo = PostgresCRUDRepository(session_factory, UserModel)
    assert (await repo.get_one_by_id(str(ada), owner_id=ada)) is not None
    assert await repo.get_one_by_id(str(bob), owner_id=ada) is None
    assert (await repo.get_one_by_id(str(bob), owner_id=None)) is not None
    scoped = await repo.get_list(1, 10, owner_id=ada)
    assert [row["id"] for row in scoped.data] == [ada]
    assert scoped.total_data == 1


async def test_owner_scoping_on_sessions(session_factory: Factory) -> None:
    ada, bob = await add_users(session_factory, 2)
    users = PostgresUserRepository(session_factory)
    expires = datetime.now(UTC) + timedelta(hours=1)
    for owner, name in ((ada, "a1"), (bob, "b1"), (ada, "a2")):
        await users.insert_oauth(
            owner, UserTokenEntity(access=f"x{name}", refresh=f"r{name}"), expires
        )
    repo = PostgresCRUDRepository(session_factory, UserTokenModel)
    scoped = await repo.get_list(1, 10, owner_id=ada)
    assert scoped.total_data == 2
    assert all(row["user_id"] == ada for row in scoped.data)
    assert all("token_hash" not in key for row in scoped.data for key in row)
    assert (await repo.get_list(1, 10, owner_id=None)).total_data == 3


async def test_permissions_model(session_factory: Factory) -> None:
    (ada,) = await add_users(session_factory, 1)
    async with session_factory.begin() as session:
        session.add(UserPermissionTable(user_id=ada, permission="admin"))
    repo = PostgresCRUDRepository(session_factory, UserPermissionModel)
    listing = await repo.get_list(1, 10, owner_id=ada)
    assert [row["permission"] for row in listing.data] == ["admin"]


async def test_order_count_and_total_page(session_factory: Factory) -> None:
    ids = await add_users(session_factory, 25)
    repo = PostgresCRUDRepository(session_factory, UserModel)
    first = await repo.get_list(1, 10, owner_id=None)
    assert [row["id"] for row in first.data] == ids[:10]
    assert (first.total_data, first.total_page, first.page, first.page_size) == (25, 3, 1, 10)
    last = await repo.get_list(3, 10, owner_id=None)
    assert [row["id"] for row in last.data] == ids[20:]
    beyond = await repo.get_list(4, 10, owner_id=None)
    assert beyond.data == []
    assert beyond.total_page == 3
    assert (await repo.get_list(1, 25, owner_id=None)).total_page == 1


async def test_empty_table(session_factory: Factory) -> None:
    repo = PostgresCRUDRepository(session_factory, UserModel)
    listing = await repo.get_list(1, 10, owner_id=None)
    assert (listing.data, listing.total_data, listing.total_page) == ([], 0, 0)


@pytest.mark.parametrize(
    "record_id", ["abc", "0", "-1", "9223372036854775808", "\uff11", "", "1.5"]
)
async def test_invalid_ids_match_nothing(session_factory: Factory, record_id: str) -> None:
    await add_users(session_factory, 1)
    repo = PostgresCRUDRepository(session_factory, UserModel)
    assert await repo.get_one_by_id(record_id, owner_id=None) is None


async def test_max_bigint_id_is_a_valid_miss(session_factory: Factory) -> None:
    repo = PostgresCRUDRepository(session_factory, UserModel)
    assert await repo.get_one_by_id(str(2**63 - 1), owner_id=None) is None

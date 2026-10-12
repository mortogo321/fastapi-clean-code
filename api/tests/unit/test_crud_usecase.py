from datetime import UTC, datetime
from typing import Any

import pytest

from app.domain.entities.user import AuthenticatedUser, UserEntity
from app.domain.errors import EntityModelNotFoundError, RecordNotFoundError
from app.usecases.application import Usecases
from tests.fakes import FakeCRUDRepository


def caller(user_id: int, permission: str | None = None) -> AuthenticatedUser:
    now = datetime.now(UTC)
    entity = UserEntity(
        id=user_id, email="a@b.co", first_name="a", last_name="b", created_at=now, updated_at=now
    )
    return AuthenticatedUser(user=entity, permission=permission)


def token_row(row_id: int, user_id: int) -> dict[str, Any]:
    return {"id": row_id, "user_id": user_id}


@pytest.fixture(autouse=True)
def seeded(crud_repos: dict[str, FakeCRUDRepository]) -> None:
    crud_repos["user-tokens"].rows = [token_row(1, 1), token_row(2, 2), token_row(3, 1)]


async def test_regular_user_is_scoped_to_own_rows(usecases: Usecases) -> None:
    response = await usecases.crud.retrieve_list(caller(1), "user-tokens", 1, 10)
    assert [row["id"] for row in response.data] == [1, 3]
    assert response.total_data == 2


async def test_admin_sees_everything(usecases: Usecases) -> None:
    response = await usecases.crud.retrieve_list(caller(1, "admin"), "user-tokens", 1, 10)
    assert [row["id"] for row in response.data] == [1, 2, 3]
    assert (await usecases.crud.retrieve(caller(1, "admin"), "user-tokens", "2")).data["id"] == 2


async def test_retrieve_own_and_foreign_record(usecases: Usecases) -> None:
    assert (await usecases.crud.retrieve(caller(1), "user-tokens", "3")).data["id"] == 3
    with pytest.raises(RecordNotFoundError):
        await usecases.crud.retrieve(caller(1), "user-tokens", "2")


async def test_missing_record(usecases: Usecases) -> None:
    with pytest.raises(RecordNotFoundError):
        await usecases.crud.retrieve(caller(1), "user-tokens", "99")


async def test_unknown_slug(usecases: Usecases) -> None:
    with pytest.raises(EntityModelNotFoundError):
        await usecases.crud.retrieve(caller(1), "nope", "1")
    with pytest.raises(EntityModelNotFoundError):
        await usecases.crud.retrieve_list(caller(1), "nope", 1, 10)
    with pytest.raises(EntityModelNotFoundError):
        usecases.crud.describe_data_source("nope")


def test_list_and_describe(usecases: Usecases) -> None:
    assert usecases.crud.list_data_models() == ["users", "user-tokens", "user-permissions"]
    assert usecases.crud.describe_data_source("users")["name"] == "user-model"

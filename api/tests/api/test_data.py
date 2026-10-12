from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from tests.api.helpers import bearer, register_and_login
from tests.fakes import FakeCRUDRepository, FakeUserRepository

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def token_rows(count: int, user_id: int, start: int = 1) -> list[dict[str, Any]]:
    return [
        {
            "id": start + i,
            "user_id": user_id,
            "expires_at": NOW,
            "created_at": NOW,
            "updated_at": NOW,
        }
        for i in range(count)
    ]


@pytest.fixture
async def auth(client: httpx.AsyncClient) -> dict[str, str]:
    tokens = await register_and_login(client)
    return bearer(tokens["token"]["access"])


@pytest.mark.parametrize("path", ["/api/v1/data/", "/api/v1/data/users/", "/api/v1/data/users/1"])
async def test_requires_auth(client: httpx.AsyncClient, path: str) -> None:
    response = await client.get(path)
    assert response.status_code == 401
    assert response.json()["trace_id"] == "middleware-002"


async def test_list_models(client: httpx.AsyncClient, auth: dict[str, str]) -> None:
    response = await client.get("/api/v1/data/", headers=auth)
    assert response.status_code == 200
    assert response.json() == {"data": ["users", "user-tokens", "user-permissions"]}


async def test_describe(client: httpx.AsyncClient, auth: dict[str, str]) -> None:
    response = await client.get("/api/v1/data/users/describe", headers=auth)
    assert response.status_code == 200
    schema = response.json()
    assert schema["type"] == "record"
    assert schema["name"] == "user-model"
    assert {"name": "email", "type": "string"} in schema["fields"]
    assert "password_hash" not in response.text


async def test_unknown_slug(client: httpx.AsyncClient, auth: dict[str, str]) -> None:
    for path in ("describe", "", "1"):
        response = await client.get(f"/api/v1/data/nope/{path}", headers=auth)
        assert response.status_code == 404
        assert response.json()["trace_id"] == "data-001"


async def test_retrieve_own_record(
    client: httpx.AsyncClient, auth: dict[str, str], crud_repos: dict[str, FakeCRUDRepository]
) -> None:
    crud_repos["users"].rows = [{"id": 1, "email": "ada@example.com"}, {"id": 2, "email": "x@y.z"}]
    response = await client.get("/api/v1/data/users/1", headers=auth)
    assert response.status_code == 200
    assert response.json()["data"]["email"] == "ada@example.com"
    assert response.json()["data_schema"]["name"] == "user-model"


@pytest.mark.parametrize("record_id", ["2", "999", "abc", "0", "-1", "9223372036854775808"])
async def test_record_not_found(
    client: httpx.AsyncClient,
    auth: dict[str, str],
    crud_repos: dict[str, FakeCRUDRepository],
    record_id: str,
) -> None:
    crud_repos["users"].rows = [{"id": 1, "email": "ada@example.com"}, {"id": 2, "email": "x@y.z"}]
    response = await client.get(f"/api/v1/data/users/{record_id}", headers=auth)
    assert response.status_code == 404
    assert response.json() == {"trace_id": "data-002", "message": "record not found"}


@pytest.mark.parametrize(
    "query", ["_pageSize=101", "_pageSize=0", "_page=0", "_page=-1", "_page=x"]
)
async def test_paging_validation(
    client: httpx.AsyncClient, auth: dict[str, str], query: str
) -> None:
    response = await client.get(f"/api/v1/data/user-tokens/?{query}", headers=auth)
    assert response.status_code == 422
    assert response.json()["trace_id"] == "middleware-003"
    assert response.json()["details"][0]["field"] in {"_page", "_pageSize"}


async def test_paging_math(
    client: httpx.AsyncClient, auth: dict[str, str], crud_repos: dict[str, FakeCRUDRepository]
) -> None:
    crud_repos["user-tokens"].rows = token_rows(25, 1) + token_rows(5, 2, start=100)
    response = await client.get("/api/v1/data/user-tokens/?_pageSize=10&_page=3", headers=auth)
    body = response.json()
    assert response.status_code == 200
    assert (body["page"], body["page_size"]) == (3, 10)
    assert (body["total_data"], body["total_page"]) == (25, 3)
    assert [row["id"] for row in body["data"]] == [21, 22, 23, 24, 25]

    default = (await client.get("/api/v1/data/user-tokens/", headers=auth)).json()
    assert (default["page"], default["page_size"], len(default["data"])) == (1, 10, 10)

    exact = (await client.get("/api/v1/data/user-tokens/?_pageSize=25", headers=auth)).json()
    assert exact["total_page"] == 1

    past_end = (await client.get("/api/v1/data/user-tokens/?_page=9", headers=auth)).json()
    assert past_end["data"] == []
    assert past_end["total_page"] == 3


async def test_empty_list(client: httpx.AsyncClient, auth: dict[str, str]) -> None:
    body = (await client.get("/api/v1/data/user-tokens/", headers=auth)).json()
    assert (body["data"], body["total_data"], body["total_page"]) == ([], 0, 0)


async def test_admin_sees_all_rows(
    client: httpx.AsyncClient,
    auth: dict[str, str],
    crud_repos: dict[str, FakeCRUDRepository],
    user_repo: FakeUserRepository,
) -> None:
    crud_repos["user-tokens"].rows = token_rows(3, 1) + token_rows(2, 2, start=10)
    assert (await client.get("/api/v1/data/user-tokens/", headers=auth)).json()["total_data"] == 3
    user_repo.grant(1, "admin")
    assert (await client.get("/api/v1/data/user-tokens/", headers=auth)).json()["total_data"] == 5
    assert (await client.get("/api/v1/data/user-tokens/10", headers=auth)).status_code == 200

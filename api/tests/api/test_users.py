import httpx

from tests.api.helpers import EMAIL, PASSWORD, bearer, login, register, register_and_login


async def test_register_created(client: httpx.AsyncClient) -> None:
    response = await register(client, "Ada@Example.com")
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "email", "first_name", "last_name", "created_at", "updated_at"}
    assert body["email"] == EMAIL
    assert PASSWORD not in response.text
    assert "password" not in response.text


async def test_register_duplicate(client: httpx.AsyncClient) -> None:
    await register(client)
    response = await register(client, "ADA@example.com")
    assert response.status_code == 409
    assert response.json() == {"trace_id": "users-001", "message": "email is already registered"}


async def test_register_invalid_input(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/api/v1/users/register",
        json={"email": EMAIL, "password": "short", "first_name": "Ada", "last_name": "L"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["trace_id"] == "middleware-003"
    assert body["details"][0]["field"] == "password"
    assert body["details"][0]["message"]
    assert body["message"].startswith("password: ")


async def test_register_rejects_extra_and_multibyte_password(client: httpx.AsyncClient) -> None:
    extra = await client.post(
        "/api/v1/users/register",
        json={
            "email": EMAIL,
            "password": PASSWORD,
            "first_name": "A",
            "last_name": "L",
            "is_admin": True,
        },
    )
    assert extra.status_code == 422
    assert extra.json()["details"][0]["field"] == "is_admin"
    long_password = await client.post(
        "/api/v1/users/register",
        json={"email": EMAIL, "password": "ก" * 25, "first_name": "A", "last_name": "L"},
    )
    assert long_password.status_code == 422
    assert long_password.json()["details"][0]["field"] == "password"


async def test_login_ok(client: httpx.AsyncClient) -> None:
    await register(client)
    response = await client.post("/api/v1/users/login", json={"email": EMAIL, "password": PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == EMAIL
    assert body["token"]["access"]
    assert body["token"]["refresh"]
    assert "password" not in response.text


async def test_login_failures_are_identical(client: httpx.AsyncClient) -> None:
    await register(client)
    wrong = await client.post("/api/v1/users/login", json={"email": EMAIL, "password": "nope-nope"})
    unknown = await client.post(
        "/api/v1/users/login", json={"email": "who@example.com", "password": PASSWORD}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert wrong.json() == {"trace_id": "users-002", "message": "invalid email or password"}


async def test_profile_requires_bearer(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/users/profile")
    assert response.status_code == 401
    assert response.json()["trace_id"] == "middleware-002"
    assert response.headers["www-authenticate"] == "Bearer"


async def test_profile_garbage_token(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/users/profile", headers=bearer("garbage"))
    assert response.status_code == 401
    assert response.json() == {"trace_id": "middleware-002", "message": "token is invalid"}
    assert response.headers["www-authenticate"] == "Bearer"


async def test_profile_ok(client: httpx.AsyncClient) -> None:
    tokens = await register_and_login(client)
    response = await client.get("/api/v1/users/profile", headers=bearer(tokens["token"]["access"]))
    assert response.status_code == 200
    assert response.json()["email"] == EMAIL


async def test_profile_rejects_refresh_token(client: httpx.AsyncClient) -> None:
    tokens = await register_and_login(client)
    response = await client.get("/api/v1/users/profile", headers=bearer(tokens["token"]["refresh"]))
    assert response.status_code == 401


async def test_refresh_rotates_and_old_token_fails(client: httpx.AsyncClient) -> None:
    tokens = (await register_and_login(client))["token"]
    response = await client.post(
        "/api/v1/users/refresh-token", json={"refresh_token": tokens["refresh"]}
    )
    assert response.status_code == 200
    new = response.json()["token"]
    assert new["access"] != tokens["access"]
    assert new["refresh"] != tokens["refresh"]

    reuse = await client.post(
        "/api/v1/users/refresh-token", json={"refresh_token": tokens["refresh"]}
    )
    assert reuse.status_code == 401
    assert reuse.json() == {"trace_id": "users-003", "message": "token has been revoked"}

    old_access = await client.get("/api/v1/users/profile", headers=bearer(tokens["access"]))
    assert old_access.status_code == 401
    new_access = await client.get("/api/v1/users/profile", headers=bearer(new["access"]))
    assert new_access.status_code == 200


async def test_refresh_with_access_token(client: httpx.AsyncClient) -> None:
    tokens = (await register_and_login(client))["token"]
    response = await client.post(
        "/api/v1/users/refresh-token", json={"refresh_token": tokens["access"]}
    )
    assert response.status_code == 401
    assert response.json()["trace_id"] == "users-003"


async def test_logout_flow(client: httpx.AsyncClient) -> None:
    tokens = (await register_and_login(client))["token"]
    response = await client.post("/api/v1/users/logout", json={"refresh_token": tokens["refresh"]})
    assert response.status_code == 204
    assert response.content == b""

    profile = await client.get("/api/v1/users/profile", headers=bearer(tokens["access"]))
    assert profile.status_code == 401

    again = await client.post("/api/v1/users/logout", json={"refresh_token": tokens["refresh"]})
    assert again.status_code == 401
    assert again.json() == {"trace_id": "users-004", "message": "token has been revoked"}


async def test_second_session_survives_logout(client: httpx.AsyncClient) -> None:
    first = (await register_and_login(client))["token"]
    second = (await login(client))["token"]
    await client.post("/api/v1/users/logout", json={"refresh_token": first["refresh"]})
    response = await client.get("/api/v1/users/profile", headers=bearer(second["access"]))
    assert response.status_code == 200

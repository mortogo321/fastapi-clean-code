from typing import Any

import httpx

PASSWORD = "password123"
EMAIL = "ada@example.com"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def register(client: httpx.AsyncClient, email: str = EMAIL) -> httpx.Response:
    return await client.post(
        "/api/v1/users/register",
        json={"email": email, "password": PASSWORD, "first_name": "Ada", "last_name": "L"},
    )


async def login(client: httpx.AsyncClient, email: str = EMAIL) -> dict[str, Any]:
    response = await client.post("/api/v1/users/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    body: dict[str, Any] = response.json()
    return body


async def register_and_login(client: httpx.AsyncClient, email: str = EMAIL) -> dict[str, Any]:
    assert (await register(client, email)).status_code == 201
    return await login(client, email)

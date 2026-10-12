from collections.abc import AsyncIterator
from datetime import timedelta

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config.crud_models import CRUD_MODELS
from app.config.settings import Settings
from app.infrastructure.fastapi.server.server import create_app
from app.interface.repositories.postgres.crud import PostgresCRUDRepository
from app.interface.repositories.postgres.user import PostgresUserRepository
from app.shared.authentication.jwt import JWTAuthentication
from app.shared.authentication.password import PasswordHasher
from app.usecases.application import Usecases
from app.usecases.crud import CRUDUsecase
from app.usecases.user import UserUsecase
from tests.api.helpers import EMAIL, PASSWORD, bearer


@pytest.fixture
async def real_client(
    settings: Settings, session_factory: async_sessionmaker[AsyncSession]
) -> AsyncIterator[httpx.AsyncClient]:
    jwt_auth = JWTAuthentication(
        secret_key=settings.secret_key.get_secret_value(),
        issuer=settings.jwt_issuer,
        access_expires=timedelta(seconds=settings.jwt_access_expires),
        refresh_expires=timedelta(seconds=settings.jwt_refresh_expires),
    )
    app = create_app(settings)
    app.state.usecases = Usecases(
        user=UserUsecase(PostgresUserRepository(session_factory), jwt_auth, PasswordHasher(4)),
        crud=CRUDUsecase(
            {
                model.crud_slug(): PostgresCRUDRepository(session_factory, model)
                for model in CRUD_MODELS
            }
        ),
    )
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_full_flow(real_client: httpx.AsyncClient) -> None:
    client = real_client
    register = await client.post(
        "/api/v1/users/register",
        json={"email": EMAIL, "password": PASSWORD, "first_name": "Ada", "last_name": "L"},
    )
    assert register.status_code == 201
    user_id = register.json()["id"]

    duplicate = await client.post(
        "/api/v1/users/register",
        json={"email": EMAIL, "password": PASSWORD, "first_name": "Ada", "last_name": "L"},
    )
    assert duplicate.status_code == 409

    login = await client.post("/api/v1/users/login", json={"email": EMAIL, "password": PASSWORD})
    assert login.status_code == 200
    token = login.json()["token"]

    profile = await client.get("/api/v1/users/profile", headers=bearer(token["access"]))
    assert profile.status_code == 200
    assert profile.json()["id"] == user_id

    data = await client.get("/api/v1/data/users/", headers=bearer(token["access"]))
    assert data.status_code == 200
    body = data.json()
    assert [row["id"] for row in body["data"]] == [user_id]
    assert "password_hash" not in data.text
    assert body["total_data"] == 1

    refreshed = await client.post(
        "/api/v1/users/refresh-token", json={"refresh_token": token["refresh"]}
    )
    assert refreshed.status_code == 200
    new = refreshed.json()["token"]
    assert (
        await client.get("/api/v1/users/profile", headers=bearer(token["access"]))
    ).status_code == 401
    assert (
        await client.post("/api/v1/users/refresh-token", json={"refresh_token": token["refresh"]})
    ).status_code == 401

    logout = await client.post("/api/v1/users/logout", json={"refresh_token": new["refresh"]})
    assert logout.status_code == 204
    assert (
        await client.get("/api/v1/users/profile", headers=bearer(new["access"]))
    ).status_code == 401
    assert (
        await client.post("/api/v1/users/logout", json={"refresh_token": new["refresh"]})
    ).status_code == 401

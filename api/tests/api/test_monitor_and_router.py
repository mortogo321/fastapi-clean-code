import httpx
from fastapi import FastAPI

from app.config.settings import Settings
from app.infrastructure.fastapi.server.server import create_app
from app.shared.authentication.jwt import JWTAuthentication
from app.shared.authentication.password import PasswordHasher
from app.usecases.application import Usecases
from app.usecases.user import UserUsecase
from tests.api.helpers import EMAIL, PASSWORD
from tests.fakes import FakeUserRepository


async def test_monitor(client: httpx.AsyncClient, settings: Settings) -> None:
    response = await client.get("/api/v1/")
    assert response.status_code == 200
    assert response.json() == {"name": settings.name, "version": settings.version}


async def test_root_redirects_to_api_v1(client: httpx.AsyncClient, app: FastAPI) -> None:
    response = await client.get("/")
    assert response.status_code == 307
    assert response.headers["location"] == "/api/v1/"
    assert "/" not in app.openapi()["paths"]


async def test_unknown_route(client: httpx.AsyncClient) -> None:
    response = await client.get("/api/v1/nope")
    assert response.status_code == 404
    assert response.json() == {"trace_id": "middleware-001", "message": "router not found"}


async def test_wrong_method(client: httpx.AsyncClient) -> None:
    response = await client.put("/api/v1/users/login")
    assert response.status_code == 405
    body = response.json()
    assert body["trace_id"] == "middleware-001"
    assert body["message"] == "method not allowed"
    assert "POST" in response.headers["allow"]


async def test_unhandled_exception_does_not_leak(
    settings: Settings, usecases: Usecases, jwt_auth: JWTAuthentication, hasher: PasswordHasher
) -> None:
    class ExplodingRepository(FakeUserRepository):
        async def get_user_by_email(self, email: str) -> None:
            raise RuntimeError("secret database password hunter2")

    app: FastAPI = create_app(settings)
    app.state.usecases = Usecases(
        user=UserUsecase(ExplodingRepository(), jwt_auth, hasher),
        crud=usecases.crud,
    )
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/users/login", json={"email": EMAIL, "password": PASSWORD}
        )
    assert response.status_code == 500
    assert response.json() == {"trace_id": "middleware-000", "message": "internal server error"}
    assert "hunter2" not in response.text
    assert "RuntimeError" not in response.text

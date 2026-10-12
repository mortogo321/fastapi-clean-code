"""Shared fixtures: settings, auth helpers, fakes, the app and an ASGI client."""

from collections.abc import AsyncIterator
from datetime import timedelta

import httpx
import pytest
from fastapi import FastAPI
from pydantic import SecretStr

from app.config.crud_models import CRUD_MODELS
from app.config.settings import Settings
from app.infrastructure.fastapi.server.server import create_app
from app.shared.authentication.jwt import JWTAuthentication
from app.shared.authentication.password import PasswordHasher
from app.usecases.application import Usecases
from app.usecases.crud import CRUDUsecase
from app.usecases.user import UserUsecase
from tests.fakes import FakeCRUDRepository, FakeUserRepository


@pytest.fixture
def settings() -> Settings:
    return Settings(
        name="FastAPI Clean Code",
        version="0.1.0",
        secret_key=SecretStr("x" * 32),
        bcrypt_rounds=4,
        jwt_access_expires=900,
        jwt_refresh_expires=3600,
        cors_origins=[],
        docs_enabled=False,
        _env_file=None,
    )


@pytest.fixture
def jwt_auth(settings: Settings) -> JWTAuthentication:
    return JWTAuthentication(
        secret_key=settings.secret_key.get_secret_value(),
        issuer=settings.jwt_issuer,
        access_expires=timedelta(seconds=settings.jwt_access_expires),
        refresh_expires=timedelta(seconds=settings.jwt_refresh_expires),
    )


@pytest.fixture(scope="session")
def hasher() -> PasswordHasher:
    return PasswordHasher(4)


@pytest.fixture
def user_repo() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture
def crud_repos() -> dict[str, FakeCRUDRepository]:
    return {model.crud_slug(): FakeCRUDRepository(model) for model in CRUD_MODELS}


@pytest.fixture
def usecases(
    user_repo: FakeUserRepository,
    crud_repos: dict[str, FakeCRUDRepository],
    jwt_auth: JWTAuthentication,
    hasher: PasswordHasher,
) -> Usecases:
    return Usecases(
        user=UserUsecase(user_repo, jwt_auth, hasher),
        crud=CRUDUsecase(dict(crud_repos)),
    )


@pytest.fixture
def app(settings: Settings, usecases: Usecases) -> FastAPI:
    application = create_app(settings)
    application.state.usecases = usecases
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client

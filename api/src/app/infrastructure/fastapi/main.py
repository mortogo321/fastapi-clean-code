"""Composition root (port of gofiber/main.go): ``uvicorn app.infrastructure.fastapi.main:app``.

The only place that knows every concrete class: it wires settings, database,
repositories and use cases, then hands the use cases to the HTTP layer.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config.crud_models import CRUD_MODELS
from app.config.settings import Settings, get_postgres_settings, get_settings
from app.infrastructure.database.postgres.connector import postgres_session_factory
from app.infrastructure.fastapi.server.server import create_app
from app.interface.repositories.postgres.crud import PostgresCRUDRepository
from app.interface.repositories.postgres.user import PostgresUserRepository
from app.shared.authentication.jwt import JWTAuthentication
from app.shared.authentication.password import PasswordHasher
from app.shared.crud.const import DatasourceType
from app.usecases.application import Usecases
from app.usecases.crud import CRUDUsecase
from app.usecases.user import UserUsecase


def build_usecases(
    settings: Settings, session_factory: async_sessionmaker[AsyncSession]
) -> Usecases:
    jwt_authentication = JWTAuthentication(
        secret_key=settings.secret_key.get_secret_value(),
        issuer=settings.jwt_issuer,
        access_expires=timedelta(seconds=settings.jwt_access_expires),
        refresh_expires=timedelta(seconds=settings.jwt_refresh_expires),
    )
    user_usecase = UserUsecase(
        PostgresUserRepository(session_factory),
        jwt_authentication,
        PasswordHasher(settings.bcrypt_rounds),
    )
    crud_usecase = CRUDUsecase(
        {
            model.crud_slug(): PostgresCRUDRepository(session_factory, model)
            for model in CRUD_MODELS
            if model.datasource is DatasourceType.POSTGRESQL
        }
    )
    return Usecases(user=user_usecase, crud=crud_usecase)


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with postgres_session_factory(get_postgres_settings()) as session_factory:
        app.state.usecases = build_usecases(settings, session_factory)
        yield


app = create_app(settings, lifespan)

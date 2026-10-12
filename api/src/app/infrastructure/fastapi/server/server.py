"""FastAPI application factory (port of server/server.go)."""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from starlette.types import Lifespan

from app.config.settings import Settings
from app.infrastructure.fastapi.server.middlewares import EXCEPTION_HANDLERS, cors_middleware
from app.infrastructure.fastapi.server.module import register_modules


def create_app(settings: Settings, lifespan: Lifespan[FastAPI] | None = None) -> FastAPI:
    app = FastAPI(
        title=settings.name,
        version=settings.version,
        lifespan=lifespan,
        docs_url="/swagger" if settings.docs_enabled else None,
        redoc_url=None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
        middleware=[cors_middleware(settings.cors_origins)],
        exception_handlers=EXCEPTION_HANDLERS,
    )
    register_modules(app)

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse("/api/v1/")

    return app

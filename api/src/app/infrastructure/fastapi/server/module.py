"""Route registration (port of server/module.go)."""

from fastapi import APIRouter, FastAPI

from app.interface.handlers.fastapi.modules import crud, monitor, user


def register_modules(app: FastAPI) -> None:
    api_v1 = APIRouter(prefix="/api/v1")
    api_v1.include_router(monitor.router)
    api_v1.include_router(user.router)
    api_v1.include_router(crud.router)
    app.include_router(api_v1)

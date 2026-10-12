"""``GET /api/v1/`` (port of modules/monitor/monitor.go)."""

from fastapi import APIRouter, Request

from app.domain.entities.monitor import Monitor

router = APIRouter(tags=["Monitor"])


@router.get("/", summary="Name and version of the server")
async def health_check(request: Request) -> Monitor:
    return Monitor(name=request.app.title, version=request.app.version)

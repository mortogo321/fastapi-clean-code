"""CORS and error rendering for every response (port of server/middlewares.go)."""

from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from app.interface.handlers.fastapi.entities import APIError, ErrorCode, ErrorDetail, ErrorResponse


def cors_middleware(origins: Sequence[str]) -> Middleware:
    return Middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type"],
    )


def _error_response(
    status_code: int,
    code: ErrorCode,
    message: str,
    details: list[ErrorDetail] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(trace_id=code, message=message, details=details)
    return JSONResponse(body.model_dump(exclude_none=True), status_code, headers)


async def _api_error(_: Request, error: APIError) -> JSONResponse:
    return _error_response(error.status_code, error.code, error.message, headers=error.headers)


async def _validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
    details = [
        # ("body", "password") -> "password"; keep the location when it is the only part.
        ErrorDetail(
            field=".".join(map(str, item["loc"][1:])) or str(item["loc"][0]), message=item["msg"]
        )
        for item in error.errors()
    ]
    message = "; ".join(f"{detail.field}: {detail.message}" for detail in details)
    return _error_response(
        status.HTTP_422_UNPROCESSABLE_CONTENT, ErrorCode.VALIDATION, message, details
    )


async def _router_error(_: Request, error: HTTPException) -> JSONResponse:
    # Raised by the router itself: unknown path (404) or method (405).
    message = "router not found" if error.status_code == 404 else str(error.detail).lower()
    return _error_response(
        error.status_code, ErrorCode.ROUTER_NOT_FOUND, message, headers=error.headers
    )


async def _internal_error(_: Request, __: Exception) -> JSONResponse:
    # Never leak internals; the exception is still re-raised to the server, which logs it.
    return _error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR, ErrorCode.INTERNAL, "internal server error"
    )


EXCEPTION_HANDLERS: dict[int | type[Exception], Any] = {
    APIError: _api_error,
    RequestValidationError: _validation_error,
    HTTPException: _router_error,
    Exception: _internal_error,
}

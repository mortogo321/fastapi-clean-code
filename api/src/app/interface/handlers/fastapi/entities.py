"""HTTP error contract (port of interface/handlers/gofiber/entities/response.go)."""

from collections.abc import Mapping
from enum import StrEnum

from pydantic import BaseModel


class ErrorCode(StrEnum):
    INTERNAL = "middleware-000"
    ROUTER_NOT_FOUND = "middleware-001"
    JWT_AUTH = "middleware-002"
    VALIDATION = "middleware-003"
    REGISTER_USER = "users-001"
    LOGIN_USER = "users-002"
    REFRESH_TOKEN = "users-003"  # noqa: S105 - an error code, not a credential
    LOGOUT_USER = "users-004"
    DATA_MODEL = "data-001"
    DATA_RECORD = "data-002"


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    trace_id: str  # the ErrorCode, as in the Go API
    message: str
    details: list[ErrorDetail] | None = None


class APIError(Exception):
    """Raised by route handlers; rendered as an ``ErrorResponse``."""

    def __init__(
        self,
        status_code: int,
        code: ErrorCode,
        message: str,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.headers = headers

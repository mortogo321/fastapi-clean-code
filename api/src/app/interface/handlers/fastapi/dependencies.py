"""Dependencies shared by the route modules."""

from typing import Annotated, cast

from fastapi import Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domain.entities.user import AuthenticatedUser
from app.domain.errors import InvalidTokenError
from app.interface.handlers.fastapi.entities import APIError, ErrorCode
from app.usecases.application import Usecases


def get_usecases(request: Request) -> Usecases:
    return cast(Usecases, request.app.state.usecases)


UsecasesDep = Annotated[Usecases, Depends(get_usecases)]

_bearer = HTTPBearer(auto_error=False)


async def jwt_auth(
    usecases: UsecasesDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthenticatedUser:
    """Resolve the caller from ``Authorization: Bearer <access token>`` (Go ``JwtAuth``)."""
    if credentials is None:
        raise _unauthorized("missing bearer token")
    try:
        return await usecases.user.user_authentication(credentials.credentials)
    except InvalidTokenError as error:
        raise _unauthorized(str(error)) from error


CurrentUser = Annotated[AuthenticatedUser, Depends(jwt_auth)]


def _unauthorized(message: str) -> APIError:
    return APIError(
        status.HTTP_401_UNAUTHORIZED,
        ErrorCode.JWT_AUTH,
        message,
        headers={"WWW-Authenticate": "Bearer"},
    )

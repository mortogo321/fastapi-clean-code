"""``/api/v1/users`` (port of modules/user/user.go)."""

from typing import Any

from fastapi import APIRouter, status

from app.domain.entities.user import (
    UserEntity,
    UserLoginRequest,
    UserLoginResponse,
    UserRefreshTokenRequest,
    UserRegisterRequest,
)
from app.domain.errors import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidTokenError,
)
from app.interface.handlers.fastapi.dependencies import CurrentUser, UsecasesDep
from app.interface.handlers.fastapi.entities import APIError, ErrorCode, ErrorResponse

router = APIRouter(
    prefix="/users",
    tags=["User"],
    responses={status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse}},
)

_UNAUTHORIZED: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse}
}


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_409_CONFLICT: {"model": ErrorResponse}},
)
async def register_user(payload: UserRegisterRequest, usecases: UsecasesDep) -> UserEntity:
    try:
        return await usecases.user.register_user(payload)
    except EmailAlreadyRegisteredError as error:
        raise APIError(status.HTTP_409_CONFLICT, ErrorCode.REGISTER_USER, str(error)) from error


@router.post("/login", responses=_UNAUTHORIZED)
async def user_login(payload: UserLoginRequest, usecases: UsecasesDep) -> UserLoginResponse:
    try:
        return await usecases.user.user_login(payload)
    except InvalidCredentialsError as error:
        raise APIError(status.HTTP_401_UNAUTHORIZED, ErrorCode.LOGIN_USER, str(error)) from error


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, responses=_UNAUTHORIZED)
async def user_logout(payload: UserRefreshTokenRequest, usecases: UsecasesDep) -> None:
    try:
        await usecases.user.user_logout(payload)
    except InvalidTokenError as error:
        raise APIError(status.HTTP_401_UNAUTHORIZED, ErrorCode.LOGOUT_USER, str(error)) from error


@router.post("/refresh-token", responses=_UNAUTHORIZED)
async def refresh_token(
    payload: UserRefreshTokenRequest, usecases: UsecasesDep
) -> UserLoginResponse:
    try:
        return await usecases.user.user_refresh_token(payload)
    except InvalidTokenError as error:
        raise APIError(status.HTTP_401_UNAUTHORIZED, ErrorCode.REFRESH_TOKEN, str(error)) from error


@router.get("/profile", responses=_UNAUTHORIZED)
async def get_user_profile(current_user: CurrentUser) -> UserEntity:
    return current_user.user

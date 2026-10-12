"""User entities and request/response contracts (port of domain/entities/user/*.go)."""

from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, StringConstraints

ADMIN_PERMISSION = "admin"
_BCRYPT_MAX_BYTES = 72


def _check_bcrypt_limit(password: str) -> str:
    # bcrypt only reads 72 bytes and bcrypt>=5 rejects longer input instead of truncating it.
    if len(password.encode()) > _BCRYPT_MAX_BYTES:
        raise ValueError(f"password must be at most {_BCRYPT_MAX_BYTES} bytes")
    return password


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class UserEntity(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    created_at: datetime
    updated_at: datetime


class UserTokenEntity(BaseModel):
    access: str
    refresh: str


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserRegisterRequest(_Request):
    email: Annotated[EmailStr, AfterValidator(str.lower)]
    password: Annotated[str, Field(min_length=8), AfterValidator(_check_bcrypt_limit)]
    first_name: Name
    last_name: Name


class UserLoginRequest(_Request):
    email: Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, max_length=320)]
    password: Annotated[str, Field(min_length=1), AfterValidator(_check_bcrypt_limit)]


class UserRefreshTokenRequest(_Request):
    refresh_token: str


class UserLoginResponse(BaseModel):
    user: UserEntity
    token: UserTokenEntity


class AuthenticatedUser(BaseModel):
    """The caller behind a valid access token."""

    user: UserEntity
    permission: str | None = None

    @property
    def is_admin(self) -> bool:
        return self.permission == ADMIN_PERMISSION

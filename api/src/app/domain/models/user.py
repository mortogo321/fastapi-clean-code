"""Stored user data (port of domain/models/user.go)."""

from datetime import datetime
from typing import ClassVar

from pydantic import Field

from app.domain.entities.crud import CRUDDataModel
from app.domain.entities.user import UserEntity


class UserModel(UserEntity, CRUDDataModel):
    table_name: ClassVar[str] = "users"
    owner_field: ClassVar[str] = "id"

    password_hash: str = Field(exclude=True, repr=False)

    def to_entity(self) -> UserEntity:
        return UserEntity.model_validate(self.model_dump())


class UserTokenModel(CRUDDataModel):
    """A login session. Only token hashes are stored, and they are not part of the model."""

    table_name: ClassVar[str] = "user_tokens"
    owner_field: ClassVar[str] = "user_id"

    id: int
    user_id: int
    expires_at: datetime
    created_at: datetime
    updated_at: datetime


class UserPermissionModel(CRUDDataModel):
    table_name: ClassVar[str] = "user_permissions"
    owner_field: ClassVar[str] = "user_id"

    id: int
    user_id: int
    permission: str
    created_at: datetime
    updated_at: datetime

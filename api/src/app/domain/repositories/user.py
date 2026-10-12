"""User persistence port (port of domain/repositories/user.go)."""

from datetime import datetime
from typing import Protocol

from app.domain.entities.user import UserEntity, UserRegisterRequest, UserTokenEntity
from app.domain.models.user import UserModel, UserPermissionModel


class IUserRepository(Protocol):
    async def get_user_by_email(self, email: str) -> UserModel | None: ...

    async def insert_user(self, request: UserRegisterRequest, password_hash: str) -> UserEntity:
        """Raise ``EmailAlreadyRegisteredError`` when the email is taken."""
        ...

    async def insert_oauth(
        self, user_id: int, token: UserTokenEntity, expires_at: datetime
    ) -> None:
        """Store a new session (one per login) and prune the user's expired ones."""
        ...

    async def rotate_oauth(
        self, user_id: int, refresh_token: str, new_token: UserTokenEntity
    ) -> UserModel | None:
        """Atomically replace the live session holding ``refresh_token`` with ``new_token``.

        Return ``None`` when no live session matches (unknown, expired or already rotated).
        """
        ...

    async def delete_oauth(self, user_id: int, refresh_token: str) -> bool: ...

    async def get_user_by_access_token(self, user_id: int, access_token: str) -> UserModel | None:
        """Return the user only while the session owning ``access_token`` is live."""
        ...

    async def get_user_permission_by_user_id(self, user_id: int) -> UserPermissionModel | None: ...

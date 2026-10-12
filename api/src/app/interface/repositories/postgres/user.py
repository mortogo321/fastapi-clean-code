"""PostgreSQL ``IUserRepository`` (port of repositories/postgres/user/userRepository.go)."""

import hashlib
from datetime import datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.entities.user import UserEntity, UserRegisterRequest, UserTokenEntity
from app.domain.errors import EmailAlreadyRegisteredError
from app.domain.models.user import UserModel, UserPermissionModel
from app.interface.repositories.postgres.orm import UserPermissionTable, UserTable, UserTokenTable


class PostgresUserRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_user_by_email(self, email: str) -> UserModel | None:
        async with self._session_factory() as session:
            user = await session.scalar(select(UserTable).where(UserTable.email == email))
            return None if user is None else _to_user_model(user)

    async def insert_user(self, request: UserRegisterRequest, password_hash: str) -> UserEntity:
        statement = (
            insert(UserTable)
            .values(
                email=request.email,
                password_hash=password_hash,
                first_name=request.first_name,
                last_name=request.last_name,
            )
            .on_conflict_do_nothing(index_elements=[UserTable.email])
            .returning(UserTable)
        )
        async with self._session_factory.begin() as session:
            user = await session.scalar(statement)
            if user is None:
                raise EmailAlreadyRegisteredError
            return _to_user_model(user).to_entity()

    async def insert_oauth(
        self, user_id: int, token: UserTokenEntity, expires_at: datetime
    ) -> None:
        async with self._session_factory.begin() as session:
            await session.execute(
                delete(UserTokenTable).where(
                    UserTokenTable.user_id == user_id, UserTokenTable.expires_at <= func.now()
                )
            )
            session.add(
                UserTokenTable(
                    user_id=user_id,
                    access_token_hash=_hash_token(token.access),
                    refresh_token_hash=_hash_token(token.refresh),
                    expires_at=expires_at,
                )
            )

    async def rotate_oauth(
        self, user_id: int, refresh_token: str, new_token: UserTokenEntity
    ) -> UserModel | None:
        # Compare-and-swap on the old refresh hash: of two concurrent rotations, only one wins.
        statement = (
            update(UserTokenTable)
            .where(
                UserTokenTable.user_id == user_id,
                UserTokenTable.refresh_token_hash == _hash_token(refresh_token),
                UserTokenTable.expires_at > func.now(),
            )
            .values(
                access_token_hash=_hash_token(new_token.access),
                refresh_token_hash=_hash_token(new_token.refresh),
            )
            .returning(UserTokenTable.id)
        )
        async with self._session_factory.begin() as session:
            if await session.scalar(statement) is None:
                return None
            return _to_user_model(await session.get_one(UserTable, user_id))

    async def delete_oauth(self, user_id: int, refresh_token: str) -> bool:
        statement = (
            delete(UserTokenTable)
            .where(
                UserTokenTable.user_id == user_id,
                UserTokenTable.refresh_token_hash == _hash_token(refresh_token),
            )
            .returning(UserTokenTable.id)
        )
        async with self._session_factory.begin() as session:
            return await session.scalar(statement) is not None

    async def get_user_by_access_token(self, user_id: int, access_token: str) -> UserModel | None:
        statement = (
            select(UserTable)
            .join(UserTokenTable, UserTokenTable.user_id == UserTable.id)
            .where(
                UserTable.id == user_id,
                UserTokenTable.access_token_hash == _hash_token(access_token),
                UserTokenTable.expires_at > func.now(),
            )
        )
        async with self._session_factory() as session:
            user = await session.scalar(statement)
            return None if user is None else _to_user_model(user)

    async def get_user_permission_by_user_id(self, user_id: int) -> UserPermissionModel | None:
        statement = select(UserPermissionTable).where(UserPermissionTable.user_id == user_id)
        async with self._session_factory() as session:
            permission = await session.scalar(statement)
            if permission is None:
                return None
            return UserPermissionModel.model_validate(permission, from_attributes=True)


def _hash_token(token: str) -> str:
    """Tokens are long random-signed strings, so an unsalted SHA-256 makes a DB leak useless."""
    return hashlib.sha256(token.encode()).hexdigest()


def _to_user_model(user: UserTable) -> UserModel:
    return UserModel.model_validate(user, from_attributes=True)

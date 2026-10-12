"""In-memory test doubles that follow the repository Protocol docstrings."""

import copy
from datetime import UTC, datetime
from typing import Any

from app.domain.entities.crud import CRUDDataModel, DataListResponse, DataResponse
from app.domain.entities.user import UserEntity, UserRegisterRequest, UserTokenEntity
from app.domain.errors import EmailAlreadyRegisteredError
from app.domain.models.user import UserModel, UserPermissionModel
from app.shared.crud.avro_schema import generate_avro_schema

_MAX_BIGINT = 2**63 - 1


def _now() -> datetime:
    return datetime.now(UTC)


class _Session:
    def __init__(self, user_id: int, token: UserTokenEntity, expires_at: datetime) -> None:
        self.user_id = user_id
        self.access = token.access
        self.refresh = token.refresh
        self.expires_at = expires_at

    def is_live(self) -> bool:
        return self.expires_at > _now()


class FakeUserRepository:
    """``IUserRepository`` kept in memory (single event loop, so no locking needed)."""

    def __init__(self) -> None:
        self.users: dict[int, UserModel] = {}
        self.sessions: list[_Session] = []
        self.permissions: dict[int, UserPermissionModel] = {}
        self._next_user_id = 1

    async def get_user_by_email(self, email: str) -> UserModel | None:
        for user in self.users.values():
            if user.email == email:
                return user.model_copy()
        return None

    async def insert_user(self, request: UserRegisterRequest, password_hash: str) -> UserEntity:
        if any(user.email == request.email for user in self.users.values()):
            raise EmailAlreadyRegisteredError
        now = _now()
        user = UserModel(
            id=self._next_user_id,
            email=request.email,
            first_name=request.first_name,
            last_name=request.last_name,
            created_at=now,
            updated_at=now,
            password_hash=password_hash,
        )
        self._next_user_id += 1
        self.users[user.id] = user
        return user.to_entity()

    async def insert_oauth(
        self, user_id: int, token: UserTokenEntity, expires_at: datetime
    ) -> None:
        self.sessions = [
            session
            for session in self.sessions
            if not (session.user_id == user_id and not session.is_live())
        ]
        self.sessions.append(_Session(user_id, token, expires_at))

    async def rotate_oauth(
        self, user_id: int, refresh_token: str, new_token: UserTokenEntity
    ) -> UserModel | None:
        for session in self.sessions:
            if (
                session.user_id == user_id
                and session.refresh == refresh_token
                and session.is_live()
            ):
                session.access = new_token.access
                session.refresh = new_token.refresh
                user = self.users.get(user_id)
                return None if user is None else user.model_copy()
        return None

    async def delete_oauth(self, user_id: int, refresh_token: str) -> bool:
        for session in self.sessions:
            if session.user_id == user_id and session.refresh == refresh_token:
                self.sessions.remove(session)
                return True
        return False

    async def get_user_by_access_token(self, user_id: int, access_token: str) -> UserModel | None:
        for session in self.sessions:
            if session.user_id == user_id and session.access == access_token and session.is_live():
                user = self.users.get(user_id)
                return None if user is None else user.model_copy()
        return None

    async def get_user_permission_by_user_id(self, user_id: int) -> UserPermissionModel | None:
        return self.permissions.get(user_id)

    def grant(self, user_id: int, permission: str) -> None:
        now = _now()
        self.permissions[user_id] = UserPermissionModel(
            id=len(self.permissions) + 1,
            user_id=user_id,
            permission=permission,
            created_at=now,
            updated_at=now,
        )


class FakeCRUDRepository:
    """``ICRUDRepository`` over plain dict rows; rows carry the model's owner field."""

    def __init__(
        self, model: type[CRUDDataModel], rows: list[dict[str, Any]] | None = None
    ) -> None:
        self._owner_field = model.owner_field
        self._schema = generate_avro_schema(model)
        self.rows: list[dict[str, Any]] = rows if rows is not None else []

    def _visible(self, owner_id: int | None) -> list[dict[str, Any]]:
        rows = sorted(self.rows, key=lambda row: int(row["id"]))
        if owner_id is None:
            return rows
        return [row for row in rows if row[self._owner_field] == owner_id]

    async def get_one_by_id(self, record_id: str, owner_id: int | None) -> DataResponse | None:
        if not (record_id.isascii() and record_id.isdigit()):
            return None
        primary_key = int(record_id)
        if not 1 <= primary_key <= _MAX_BIGINT:
            return None
        for row in self._visible(owner_id):
            if row["id"] == primary_key:
                return DataResponse(data=copy.deepcopy(row), data_schema=self._schema)
        return None

    async def get_list(self, page: int, page_size: int, owner_id: int | None) -> DataListResponse:
        rows = self._visible(owner_id)
        start = (page - 1) * page_size
        return DataListResponse(
            data=copy.deepcopy(rows[start : start + page_size]),
            page=page,
            page_size=page_size,
            total_page=-(-len(rows) // page_size),
            total_data=len(rows),
            data_schema=self._schema,
        )

    def describe_data_source(self) -> dict[str, Any]:
        return self._schema

"""Read-only browsing of the published data models (port of usecases/crud/crudUsecase.go)."""

from collections.abc import Mapping
from typing import Any

from app.domain.entities.crud import DataListResponse, DataResponse
from app.domain.entities.user import AuthenticatedUser
from app.domain.errors import EntityModelNotFoundError, RecordNotFoundError
from app.domain.repositories.crud import ICRUDRepository


class CRUDUsecase:
    def __init__(self, crud_repositories: Mapping[str, ICRUDRepository]) -> None:
        """``crud_repositories`` maps each model's slug to its repository."""
        self._crud_repositories = crud_repositories

    def list_data_models(self) -> list[str]:
        return list(self._crud_repositories)

    async def retrieve(
        self, user: AuthenticatedUser, entity_model_slug: str, record_id: str
    ) -> DataResponse:
        repository = self._get_repository(entity_model_slug)
        response = await repository.get_one_by_id(record_id, owner_id=_owner_scope(user))
        if response is None:
            raise RecordNotFoundError
        return response

    async def retrieve_list(
        self, user: AuthenticatedUser, entity_model_slug: str, page: int, page_size: int
    ) -> DataListResponse:
        repository = self._get_repository(entity_model_slug)
        return await repository.get_list(page, page_size, owner_id=_owner_scope(user))

    def describe_data_source(self, entity_model_slug: str) -> dict[str, Any]:
        return self._get_repository(entity_model_slug).describe_data_source()

    def _get_repository(self, entity_model_slug: str) -> ICRUDRepository:
        repository = self._crud_repositories.get(entity_model_slug)
        if repository is None:
            raise EntityModelNotFoundError(entity_model_slug)
        return repository


def _owner_scope(user: AuthenticatedUser) -> int | None:
    """Admins read every row; everyone else only the rows they own."""
    return None if user.is_admin else user.user.id

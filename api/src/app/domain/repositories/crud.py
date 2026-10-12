"""Generic read-only persistence port (port of domain/repositories/crud.go)."""

from typing import Any, Protocol

from app.domain.entities.crud import DataListResponse, DataResponse


class ICRUDRepository(Protocol):
    """``owner_id=None`` reads every row; otherwise only rows owned by that user."""

    async def get_one_by_id(self, record_id: str, owner_id: int | None) -> DataResponse | None: ...

    async def get_list(
        self, page: int, page_size: int, owner_id: int | None
    ) -> DataListResponse: ...

    def describe_data_source(self) -> dict[str, Any]: ...

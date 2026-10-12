"""Generic data-browsing contracts (port of domain/entities/crud/*.go)."""

from typing import Any, ClassVar

from pydantic import BaseModel

from app.shared.crud.const import DatasourceType
from app.shared.crud.converter import convert_name_to_crud_slug


class CRUDDataModel(BaseModel):
    """A stored model that can be browsed through ``/api/v1/data/{slug}``."""

    table_name: ClassVar[str]
    # Column holding the owning user's id: non-admin users only see their own rows.
    owner_field: ClassVar[str]
    datasource: ClassVar[DatasourceType] = DatasourceType.POSTGRESQL

    @classmethod
    def crud_slug(cls) -> str:
        return convert_name_to_crud_slug(cls.table_name)


class DataModelsResponse(BaseModel):
    data: list[str]


class DataResponse(BaseModel):
    data: dict[str, Any]
    data_schema: dict[str, Any]


class DataListResponse(BaseModel):
    data: list[dict[str, Any]]
    page: int
    page_size: int
    total_page: int
    total_data: int
    data_schema: dict[str, Any]

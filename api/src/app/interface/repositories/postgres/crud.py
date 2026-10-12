"""Read-only repository over a ``CRUDDataModel`` table (port of postgres/crud/crudRepository.go)."""

import math
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.entities.crud import CRUDDataModel, DataListResponse, DataResponse
from app.interface.repositories.postgres.orm import Base
from app.shared.crud.avro_schema import generate_avro_schema

_MAX_BIGINT = 2**63 - 1


class PostgresCRUDRepository:
    def __init__(
        self, session_factory: async_sessionmaker[AsyncSession], model: type[CRUDDataModel]
    ) -> None:
        table = Base.metadata.tables[model.table_name]
        self._session_factory = session_factory
        self._table = table
        self._owner_column = table.c[model.owner_field]
        # Select the model's public fields only (never e.g. ``users.password_hash``).
        self._columns = [
            table.c[name] for name, field in model.model_fields.items() if not field.exclude
        ]
        self._schema = generate_avro_schema(model)

    async def get_one_by_id(self, record_id: str, owner_id: int | None) -> DataResponse | None:
        primary_key = _parse_id(record_id)
        if primary_key is None:
            return None
        statement = self._scoped(select(*self._columns), owner_id).where(
            self._table.c.id == primary_key
        )
        async with self._session_factory() as session:
            row = (await session.execute(statement)).mappings().one_or_none()
        return None if row is None else DataResponse(data=dict(row), data_schema=self._schema)

    async def get_list(self, page: int, page_size: int, owner_id: int | None) -> DataListResponse:
        count_statement = self._scoped(select(func.count()).select_from(self._table), owner_id)
        statement = (
            self._scoped(select(*self._columns), owner_id)
            .order_by(self._table.c.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        async with self._session_factory() as session:
            total = (await session.execute(count_statement)).scalar_one()
            rows = (await session.execute(statement)).mappings().all()
        return DataListResponse(
            data=[dict(row) for row in rows],
            page=page,
            page_size=page_size,
            total_page=math.ceil(total / page_size),
            total_data=total,
            data_schema=self._schema,
        )

    def describe_data_source(self) -> dict[str, Any]:
        return self._schema

    def _scoped[*Ts](self, statement: Select[*Ts], owner_id: int | None) -> Select[*Ts]:
        return statement if owner_id is None else statement.where(self._owner_column == owner_id)


def _parse_id(record_id: str) -> int | None:
    """Ids arrive as path strings; anything that is not a valid BIGINT key matches no row."""
    if not (record_id.isascii() and record_id.isdigit()):
        return None
    value = int(record_id)
    return value if 1 <= value <= _MAX_BIGINT else None

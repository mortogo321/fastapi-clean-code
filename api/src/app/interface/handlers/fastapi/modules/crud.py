"""``/api/v1/data``: read-only browsing of the published models (port of modules/crud/crud.go)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.domain.entities.crud import DataListResponse, DataModelsResponse, DataResponse
from app.domain.errors import EntityModelNotFoundError, RecordNotFoundError
from app.interface.handlers.fastapi.dependencies import CurrentUser, UsecasesDep, jwt_auth
from app.interface.handlers.fastapi.entities import APIError, ErrorCode, ErrorResponse

router = APIRouter(
    prefix="/data",
    tags=["Data"],
    dependencies=[Depends(jwt_auth)],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse},
    },
)


@router.get("/")
async def list_data_models(usecases: UsecasesDep) -> DataModelsResponse:
    return DataModelsResponse(data=usecases.crud.list_data_models())


@router.get("/{entity_model_slug}/describe")
async def describe(entity_model_slug: str, usecases: UsecasesDep) -> dict[str, Any]:
    try:
        return usecases.crud.describe_data_source(entity_model_slug)
    except EntityModelNotFoundError as error:
        raise _not_found(ErrorCode.DATA_MODEL, error) from error


@router.get("/{entity_model_slug}/")
async def retrieve_list(
    entity_model_slug: str,
    current_user: CurrentUser,
    usecases: UsecasesDep,
    page: Annotated[int, Query(alias="_page", ge=1, le=1_000_000)] = 1,
    page_size: Annotated[int, Query(alias="_pageSize", ge=1, le=100)] = 10,
) -> DataListResponse:
    try:
        return await usecases.crud.retrieve_list(current_user, entity_model_slug, page, page_size)
    except EntityModelNotFoundError as error:
        raise _not_found(ErrorCode.DATA_MODEL, error) from error


@router.get("/{entity_model_slug}/{record_id}")
async def retrieve(
    entity_model_slug: str, record_id: str, current_user: CurrentUser, usecases: UsecasesDep
) -> DataResponse:
    try:
        return await usecases.crud.retrieve(current_user, entity_model_slug, record_id)
    except EntityModelNotFoundError as error:
        raise _not_found(ErrorCode.DATA_MODEL, error) from error
    except RecordNotFoundError as error:
        raise _not_found(ErrorCode.DATA_RECORD, error) from error


def _not_found(code: ErrorCode, error: Exception) -> APIError:
    return APIError(status.HTTP_404_NOT_FOUND, code, str(error))

"""The use cases handed to delivery layers (port of domain/entities/application.go)."""

from dataclasses import dataclass

from app.usecases.crud import CRUDUsecase
from app.usecases.user import UserUsecase


@dataclass(frozen=True, slots=True)
class Usecases:
    user: UserUsecase
    crud: CRUDUsecase

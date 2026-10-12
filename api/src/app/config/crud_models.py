"""Models published through the generic ``/api/v1/data`` endpoints (port of config/crudModels.go).

To publish another model: define it in ``domain/models``, add its table to the ORM
(plus a migration), then list it here.
"""

from app.domain.entities.crud import CRUDDataModel
from app.domain.models.user import UserModel, UserPermissionModel, UserTokenModel

CRUD_MODELS: tuple[type[CRUDDataModel], ...] = (UserModel, UserTokenModel, UserPermissionModel)

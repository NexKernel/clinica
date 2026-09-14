from pydantic import BaseModel, ConfigDict

from app.schemas.types import LocalDatetime


class AuditLogRead(BaseModel):
    """Entrada de la bitácora de acciones."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    username: str | None
    role: str | None
    action: str
    module: str
    path: str
    entity_id: str | None
    status_code: int
    succeeded: bool
    ip_address: str | None
    created_at: LocalDatetime


class ModuleAccess(BaseModel):
    """Acceso de un perfil sobre un módulo del sistema."""

    code: str
    name: str
    can_view: bool
    can_manage: bool


class RolePermissions(BaseModel):
    role: str
    role_name: str
    modules: list[ModuleAccess]

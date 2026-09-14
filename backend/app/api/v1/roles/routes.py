from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.user import RoleRead
from app.services.user_admin_service import UserAdminService

router = APIRouter(prefix="/roles", tags=["roles"])


@router.get("", response_model=list[RoleRead])
def list_roles(db: DbSession, current_user: CurrentUser) -> list[RoleRead]:
    """Perfiles de acceso disponibles para asignar a los usuarios."""
    return [RoleRead.model_validate(role) for role in UserAdminService(db).list_roles()]

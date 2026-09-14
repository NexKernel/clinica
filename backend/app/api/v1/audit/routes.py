from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import AdminUser, CurrentUser, DbSession, PageParams
from app.core.permissions import PERMISSION_MATRIX, modules_for_role
from app.models import ROLE_CATALOG, RoleCode
from app.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditLogRead, ModuleAccess, RolePermissions
from app.schemas.common import Page

router = APIRouter(tags=["audit"])


@router.get("/audit", response_model=Page[AuditLogRead])
def list_audit_logs(
    db: DbSession,
    current_user: AdminUser,
    pagination: PageParams,
    search: Annotated[str | None, Query(max_length=120)] = None,
    user_id: Annotated[int | None, Query()] = None,
    module: Annotated[str | None, Query(max_length=40)] = None,
    action: Annotated[str | None, Query(max_length=10)] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> Page[AuditLogRead]:
    """Bitácora de acciones relevantes del sistema."""
    items, total = AuditRepository(db).search(
        term=search,
        user_id=user_id,
        module=module,
        action=action,
        date_from=date_from,
        date_to=date_to,
        pagination=pagination,
    )
    return Page[AuditLogRead](
        items=[AuditLogRead.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/audit/modules", response_model=list[str])
def list_audit_modules(db: DbSession, current_user: AdminUser) -> list[str]:
    return AuditRepository(db).list_modules()


@router.get("/permissions", response_model=list[RolePermissions])
def permission_matrix(current_user: AdminUser) -> list[RolePermissions]:
    """Matriz de permisos por perfil y módulo (entregable del contrato)."""
    return [
        RolePermissions(
            role=role.value,
            role_name=ROLE_CATALOG[role][0],
            modules=[ModuleAccess(**module) for module in modules_for_role(role.value)],
        )
        for role in RoleCode
    ]


@router.get("/permissions/me", response_model=RolePermissions)
def my_permissions(current_user: CurrentUser) -> RolePermissions:
    """Módulos a los que accede el usuario en sesión."""
    return RolePermissions(
        role=current_user.role,
        role_name=current_user.role_name,
        modules=[ModuleAccess(**module) for module in modules_for_role(current_user.role)],
    )


@router.get("/permissions/modules", response_model=list[str])
def list_modules(current_user: CurrentUser) -> list[str]:
    return [permission.name for permission in PERMISSION_MATRIX.values()]

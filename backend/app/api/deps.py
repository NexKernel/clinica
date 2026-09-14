from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.audit import AuditActor
from app.core.permissions import ModuleCode, can_manage, can_view
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import RoleCode, User
from app.repositories.user_repository import UserRepository
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Pagination

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]
Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Sesión no válida o expirada",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(request: Request, db: DbSession, credentials: Credentials) -> User:
    if credentials is None or not credentials.credentials:
        raise _UNAUTHORIZED

    payload = decode_access_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise _UNAUTHORIZED

    subject = payload.get("sub")
    if subject is None or not str(subject).isdigit():
        raise _UNAUTHORIZED

    user = UserRepository(db).get_by_id(int(subject))
    if user is None:
        raise _UNAUTHORIZED
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario se encuentra inactivo",
        )

    # La bitácora toma de aquí el autor: se copian los valores ahora, mientras
    # la sesión sigue abierta, porque el middleware corre después de cerrarla.
    request.state.audit_actor = AuditActor(
        id=user.id, username=user.username, role=user.role
    )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]

_FORBIDDEN_DETAIL = "No cuenta con permisos para esta operación"


def _forbidden() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_FORBIDDEN_DETAIL)


def require_roles(*roles: RoleCode) -> Callable[[User], User]:
    """Dependencia de autorización por rol."""
    allowed = {role.value for role in roles}

    def _guard(current_user: CurrentUser) -> User:
        if allowed and current_user.role not in allowed:
            raise _forbidden()
        return current_user

    return _guard


def require_view(module: ModuleCode) -> Callable[[User], User]:
    """Acceso de consulta a un módulo, según la matriz de permisos."""

    def _guard(current_user: CurrentUser) -> User:
        if not can_view(current_user.role, module):
            raise _forbidden()
        return current_user

    return _guard


def require_manage(module: ModuleCode) -> Callable[[User], User]:
    """Acceso de registro/modificación a un módulo."""

    def _guard(current_user: CurrentUser) -> User:
        if not can_manage(current_user.role, module):
            raise _forbidden()
        return current_user

    return _guard


def get_pagination(
    page: Annotated[int, Query(ge=1, description="Página solicitada")] = 1,
    page_size: Annotated[
        int, Query(ge=1, le=MAX_PAGE_SIZE, description="Registros por página")
    ] = DEFAULT_PAGE_SIZE,
) -> Pagination:
    return Pagination.of(page, page_size)


PageParams = Annotated[Pagination, Depends(get_pagination)]
AdminUser = Annotated[User, Depends(require_roles(RoleCode.ADMIN))]

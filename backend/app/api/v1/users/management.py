from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import DbSession, require_roles
from app.models import RoleCode, User
from app.schemas.user import (
    PasswordReset,
    RoleRead,
    UserAdminUpdate,
    UserCreate,
    UserListResponse,
    UserRead,
)
from app.services.user_admin_service import UserAdminService

router = APIRouter(prefix="/users", tags=["users-admin"])

AdminUser = Annotated[User, Depends(require_roles(RoleCode.ADMIN))]


@router.get("", response_model=UserListResponse)
def list_users(
    db: DbSession,
    current_user: AdminUser,
    search: Annotated[str | None, Query(max_length=120)] = None,
    role: Annotated[str | None, Query(max_length=32)] = None,
    is_active: Annotated[bool | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> UserListResponse:
    items, total = UserAdminService(db).list_users(
        term=search, role_code=role, is_active=is_active, page=page, page_size=page_size
    )
    return UserListResponse(
        items=[UserRead.model_validate(user) for user in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: DbSession, current_user: AdminUser) -> UserRead:
    return UserRead.model_validate(UserAdminService(db).create(payload))


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: DbSession, current_user: AdminUser) -> UserRead:
    return UserRead.model_validate(UserAdminService(db).get(user_id))


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int, payload: UserAdminUpdate, db: DbSession, current_user: AdminUser
) -> UserRead:
    return UserRead.model_validate(UserAdminService(db).update(user_id, payload, current_user))


@router.patch("/{user_id}/status", response_model=UserRead)
def set_user_status(
    user_id: int,
    db: DbSession,
    current_user: AdminUser,
    is_active: Annotated[bool, Body(embed=True)],
) -> UserRead:
    return UserRead.model_validate(
        UserAdminService(db).set_active(user_id, is_active, current_user)
    )


@router.post("/{user_id}/password", response_model=UserRead)
def reset_user_password(
    user_id: int, payload: PasswordReset, db: DbSession, current_user: AdminUser
) -> UserRead:
    return UserRead.model_validate(
        UserAdminService(db).reset_password(user_id, payload.new_password)
    )

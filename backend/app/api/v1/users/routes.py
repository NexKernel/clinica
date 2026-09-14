from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.user import PasswordChange, ProfileUpdate, UserRead
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def get_profile(current_user: CurrentUser) -> UserRead:
    return UserRead.model_validate(current_user)


@router.patch("/me", response_model=UserRead)
def update_profile(
    payload: ProfileUpdate, current_user: CurrentUser, db: DbSession
) -> UserRead:
    user = UserService(db).update_profile(current_user, payload)
    return UserRead.model_validate(user)


@router.post("/me/password", response_model=UserRead)
def change_password(
    payload: PasswordChange, current_user: CurrentUser, db: DbSession
) -> UserRead:
    user = UserService(db).change_password(current_user, payload)
    return UserRead.model_validate(user)

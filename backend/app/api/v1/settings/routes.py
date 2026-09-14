from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import CurrentUser, DbSession, require_roles
from app.models import RoleCode, User
from app.schemas.settings import ClinicSettingsRead, ClinicSettingsUpdate, PublicBranding
from app.services.settings_service import SettingsService

router = APIRouter(prefix="/settings", tags=["settings"])

AdminUser = Annotated[User, Depends(require_roles(RoleCode.ADMIN))]


@router.get("/public", response_model=PublicBranding)
def public_branding(db: DbSession) -> PublicBranding:
    """Identidad del establecimiento visible sin autenticación (login)."""
    return PublicBranding.model_validate(SettingsService(db).get())


@router.get("", response_model=ClinicSettingsRead)
def get_settings(db: DbSession, current_user: CurrentUser) -> ClinicSettingsRead:
    return ClinicSettingsRead.model_validate(SettingsService(db).get())


@router.put("", response_model=ClinicSettingsRead)
def update_settings(
    payload: ClinicSettingsUpdate, db: DbSession, current_user: AdminUser
) -> ClinicSettingsRead:
    return ClinicSettingsRead.model_validate(SettingsService(db).update(payload))


@router.post("/logo", response_model=ClinicSettingsRead)
async def upload_logo(
    db: DbSession,
    current_user: AdminUser,
    file: Annotated[UploadFile, File(description="Logo en PNG, JPG o WEBP")],
) -> ClinicSettingsRead:
    content = await file.read()
    updated = SettingsService(db).save_logo(content, file.content_type)
    return ClinicSettingsRead.model_validate(updated)


@router.delete("/logo", response_model=ClinicSettingsRead)
def delete_logo(db: DbSession, current_user: AdminUser) -> ClinicSettingsRead:
    return ClinicSettingsRead.model_validate(SettingsService(db).delete_logo())

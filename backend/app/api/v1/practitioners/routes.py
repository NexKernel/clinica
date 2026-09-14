from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import AdminUser, DbSession, PageParams, require_view
from app.core.permissions import ModuleCode
from app.models import User
from app.schemas.common import Page
from app.schemas.practitioner import (
    PractitionerCreate,
    PractitionerRead,
    PractitionerSummary,
    PractitionerUpdate,
)
from app.services.practitioner_service import PractitionerService

router = APIRouter(prefix="/practitioners", tags=["practitioners"])

Viewer = Annotated[User, Depends(require_view(ModuleCode.APPOINTMENTS))]


@router.get("", response_model=Page[PractitionerRead])
def list_practitioners(
    db: DbSession,
    current_user: Viewer,
    pagination: PageParams,
    search: Annotated[str | None, Query(max_length=120)] = None,
    specialty_id: Annotated[int | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
) -> Page[PractitionerRead]:
    items, total = PractitionerService(db).list_practitioners(
        term=search, specialty_id=specialty_id, is_active=is_active, pagination=pagination
    )
    return Page[PractitionerRead](
        items=[PractitionerRead.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/active", response_model=list[PractitionerSummary])
def list_active_practitioners(db: DbSession, current_user: Viewer) -> list[PractitionerSummary]:
    """Profesionales disponibles para programar citas y registrar atenciones."""
    return [
        PractitionerSummary.model_validate(item) for item in PractitionerService(db).list_active()
    ]


@router.post("", response_model=PractitionerRead, status_code=status.HTTP_201_CREATED)
def create_practitioner(
    payload: PractitionerCreate, db: DbSession, current_user: AdminUser
) -> PractitionerRead:
    return PractitionerRead.model_validate(PractitionerService(db).create(payload))


@router.get("/{practitioner_id}", response_model=PractitionerRead)
def get_practitioner(
    practitioner_id: int, db: DbSession, current_user: Viewer
) -> PractitionerRead:
    return PractitionerRead.model_validate(PractitionerService(db).get(practitioner_id))


@router.put("/{practitioner_id}", response_model=PractitionerRead)
def update_practitioner(
    practitioner_id: int, payload: PractitionerUpdate, db: DbSession, current_user: AdminUser
) -> PractitionerRead:
    return PractitionerRead.model_validate(
        PractitionerService(db).update(practitioner_id, payload)
    )


@router.patch("/{practitioner_id}/status", response_model=PractitionerRead)
def set_practitioner_status(
    practitioner_id: int,
    db: DbSession,
    current_user: AdminUser,
    is_active: Annotated[bool, Body(embed=True)],
) -> PractitionerRead:
    return PractitionerRead.model_validate(
        PractitionerService(db).set_active(practitioner_id, is_active)
    )

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import AdminUser, DbSession, PageParams, require_view
from app.core.permissions import ModuleCode
from app.models import User
from app.schemas.catalog import (
    MedicalServiceCreate,
    MedicalServiceRead,
    MedicalServiceUpdate,
    SpecialtyCreate,
    SpecialtyRead,
    SpecialtyUpdate,
)
from app.schemas.common import Page
from app.services.catalog_service import CatalogService

router = APIRouter(prefix="/catalog", tags=["catalog"])

Viewer = Annotated[User, Depends(require_view(ModuleCode.CATALOG))]


@router.get("/specialties", response_model=list[SpecialtyRead])
def list_specialties(
    db: DbSession,
    current_user: Viewer,
    only_active: Annotated[bool, Query()] = False,
) -> list[SpecialtyRead]:
    return [
        SpecialtyRead.model_validate(item)
        for item in CatalogService(db).list_specialties(only_active=only_active)
    ]


@router.post(
    "/specialties", response_model=SpecialtyRead, status_code=status.HTTP_201_CREATED
)
def create_specialty(
    payload: SpecialtyCreate, db: DbSession, current_user: AdminUser
) -> SpecialtyRead:
    return SpecialtyRead.model_validate(CatalogService(db).create_specialty(payload))


@router.put("/specialties/{specialty_id}", response_model=SpecialtyRead)
def update_specialty(
    specialty_id: int, payload: SpecialtyUpdate, db: DbSession, current_user: AdminUser
) -> SpecialtyRead:
    return SpecialtyRead.model_validate(CatalogService(db).update_specialty(specialty_id, payload))


@router.get("/services", response_model=Page[MedicalServiceRead])
def list_services(
    db: DbSession,
    current_user: Viewer,
    pagination: PageParams,
    search: Annotated[str | None, Query(max_length=120)] = None,
    kind: Annotated[str | None, Query(max_length=20)] = None,
    specialty_id: Annotated[int | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
) -> Page[MedicalServiceRead]:
    items, total = CatalogService(db).list_services(
        term=search,
        kind=kind,
        specialty_id=specialty_id,
        is_active=is_active,
        pagination=pagination,
    )
    return Page[MedicalServiceRead](
        items=[MedicalServiceRead.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/services/active", response_model=list[MedicalServiceRead])
def list_active_services(db: DbSession, current_user: Viewer) -> list[MedicalServiceRead]:
    """Tarifario vigente, usado por agenda, atenciones y caja."""
    return [
        MedicalServiceRead.model_validate(item)
        for item in CatalogService(db).list_active_services()
    ]


@router.post("/services", response_model=MedicalServiceRead, status_code=status.HTTP_201_CREATED)
def create_service(
    payload: MedicalServiceCreate, db: DbSession, current_user: AdminUser
) -> MedicalServiceRead:
    return MedicalServiceRead.model_validate(CatalogService(db).create_service(payload))


@router.put("/services/{service_id}", response_model=MedicalServiceRead)
def update_service(
    service_id: int, payload: MedicalServiceUpdate, db: DbSession, current_user: AdminUser
) -> MedicalServiceRead:
    return MedicalServiceRead.model_validate(CatalogService(db).update_service(service_id, payload))

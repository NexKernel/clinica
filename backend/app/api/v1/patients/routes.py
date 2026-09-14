from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, status

from app.api.deps import DbSession, PageParams, require_manage, require_view
from app.core.permissions import ModuleCode
from app.models import User
from app.schemas.common import Page
from app.schemas.patient import (
    PatientCreate,
    PatientRead,
    PatientStats,
    PatientSummary,
    PatientUpdate,
)
from app.services.patient_service import PatientService

router = APIRouter(prefix="/patients", tags=["patients"])

Viewer = Annotated[User, Depends(require_view(ModuleCode.PATIENTS))]
Manager = Annotated[User, Depends(require_manage(ModuleCode.PATIENTS))]


@router.get("", response_model=Page[PatientRead])
def list_patients(
    db: DbSession,
    current_user: Viewer,
    pagination: PageParams,
    search: Annotated[str | None, Query(max_length=120)] = None,
    is_active: Annotated[bool | None, Query()] = None,
) -> Page[PatientRead]:
    items, total = PatientService(db).list_patients(
        term=search, is_active=is_active, pagination=pagination
    )
    return Page[PatientRead](
        items=[PatientRead.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/search", response_model=list[PatientSummary])
def search_patients(
    db: DbSession,
    current_user: Viewer,
    term: Annotated[str, Query(min_length=2, max_length=120, description="Nombre, documento o HC")],
) -> list[PatientSummary]:
    """Búsqueda incremental usada por citas, atenciones y caja."""
    return [PatientSummary.model_validate(item) for item in PatientService(db).quick_search(term)]


@router.get("/stats", response_model=PatientStats)
def patient_stats(db: DbSession, current_user: Viewer) -> PatientStats:
    return PatientService(db).stats()


@router.get("/by-document", response_model=PatientRead | None)
def find_by_document(
    db: DbSession,
    current_user: Viewer,
    document_type: Annotated[str, Query(max_length=20)],
    document_number: Annotated[str, Query(min_length=4, max_length=20)],
) -> PatientRead | None:
    """Evita duplicados: recepción valida el documento antes de registrar."""
    patient = PatientService(db).find_by_document(document_type, document_number)
    return PatientRead.model_validate(patient) if patient else None


@router.post("", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
def create_patient(payload: PatientCreate, db: DbSession, current_user: Manager) -> PatientRead:
    return PatientRead.model_validate(PatientService(db).create(payload))


# La ficha se direcciona solo por `public_id`: el id correlativo no aparece en
# ninguna URL, ni en la barra de direcciones ni en las llamadas a la API.
PatientPublicId = Annotated[
    str, Path(min_length=32, max_length=32, pattern="^[0-9a-f]{32}$", description="public_id")
]


@router.get("/{public_id}", response_model=PatientRead)
def get_patient(public_id: PatientPublicId, db: DbSession, current_user: Viewer) -> PatientRead:
    return PatientRead.model_validate(PatientService(db).get_public(public_id))


@router.put("/{public_id}", response_model=PatientRead)
def update_patient(
    public_id: PatientPublicId, payload: PatientUpdate, db: DbSession, current_user: Manager
) -> PatientRead:
    return PatientRead.model_validate(PatientService(db).update(public_id, payload))


@router.patch("/{public_id}/status", response_model=PatientRead)
def set_patient_status(
    public_id: PatientPublicId,
    db: DbSession,
    current_user: Manager,
    is_active: Annotated[bool, Body(embed=True)],
) -> PatientRead:
    return PatientRead.model_validate(PatientService(db).set_active(public_id, is_active))

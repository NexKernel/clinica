from datetime import date
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import DbSession, PageParams, require_manage, require_view
from app.core.permissions import ModuleCode
from app.models import User
from app.schemas.common import Page
from app.schemas.encounter import (
    EncounterCreate,
    EncounterListItem,
    EncounterRead,
    EncounterUpdate,
    MedicalRecord,
)
from app.schemas.patient import PatientSummary
from app.services.encounter_service import EncounterService
from app.services.patient_service import PatientService

router = APIRouter(prefix="/encounters", tags=["encounters"])

Viewer = Annotated[User, Depends(require_view(ModuleCode.ENCOUNTERS))]
Manager = Annotated[User, Depends(require_manage(ModuleCode.ENCOUNTERS))]
RecordViewer = Annotated[User, Depends(require_view(ModuleCode.MEDICAL_RECORDS))]


@router.get("", response_model=Page[EncounterListItem])
def list_encounters(
    db: DbSession,
    current_user: Viewer,
    pagination: PageParams,
    search: Annotated[str | None, Query(max_length=120)] = None,
    patient_id: Annotated[int | None, Query()] = None,
    practitioner_id: Annotated[int | None, Query()] = None,
    encounter_status: Annotated[str | None, Query(alias="status", max_length=16)] = None,
    day: Annotated[date | None, Query()] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> Page[EncounterListItem]:
    items, total = EncounterService(db).list_encounters(
        term=search,
        patient_id=patient_id,
        practitioner_id=practitioner_id,
        status=encounter_status,
        day=day,
        date_from=date_from,
        date_to=date_to,
        pagination=pagination,
    )
    return Page[EncounterListItem](
        items=[EncounterListItem.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/record/{patient_id}", response_model=MedicalRecord)
def medical_record(patient_id: int, db: DbSession, current_user: RecordViewer) -> MedicalRecord:
    """Historia clínica del paciente: atenciones registradas, de la más reciente."""
    patient = PatientService(db).get(patient_id)
    service = EncounterService(db)
    total, last = service.record_summary(patient_id)
    return MedicalRecord(
        patient=PatientSummary.model_validate(patient),
        total_encounters=total,
        last_encounter_at=last.started_at if last else None,
        encounters=[
            EncounterListItem.model_validate(item)
            for item in service.history_for_patient(patient_id)
        ],
    )


@router.post("", response_model=EncounterRead, status_code=status.HTTP_201_CREATED)
def create_encounter(
    payload: EncounterCreate, db: DbSession, current_user: Manager
) -> EncounterRead:
    return EncounterRead.model_validate(EncounterService(db).create(payload, current_user))


@router.get("/{encounter_id}", response_model=EncounterRead)
def get_encounter(encounter_id: int, db: DbSession, current_user: Viewer) -> EncounterRead:
    return EncounterRead.model_validate(EncounterService(db).get(encounter_id))


@router.put("/{encounter_id}", response_model=EncounterRead)
def update_encounter(
    encounter_id: int, payload: EncounterUpdate, db: DbSession, current_user: Manager
) -> EncounterRead:
    return EncounterRead.model_validate(EncounterService(db).update(encounter_id, payload))


@router.post("/{encounter_id}/finish", response_model=EncounterRead)
def finish_encounter(encounter_id: int, db: DbSession, current_user: Manager) -> EncounterRead:
    """Cierra la atención y marca la cita asociada como atendida."""
    return EncounterRead.model_validate(EncounterService(db).finish(encounter_id))


@router.post("/{encounter_id}/cancel", response_model=EncounterRead)
def cancel_encounter(
    encounter_id: int,
    db: DbSession,
    current_user: Manager,
    reason: Annotated[str, Body(embed=True, min_length=3, max_length=255)],
) -> EncounterRead:
    return EncounterRead.model_validate(EncounterService(db).cancel(encounter_id, reason))

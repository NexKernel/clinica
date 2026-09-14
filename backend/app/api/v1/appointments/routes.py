from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DbSession, PageParams, require_manage, require_view
from app.core.datetime import today
from app.core.permissions import ModuleCode
from app.models import User
from app.schemas.appointment import (
    AgendaSummary,
    AppointmentCreate,
    AppointmentRead,
    AppointmentStatusChange,
    AppointmentUpdate,
    DayAvailability,
)
from app.schemas.common import Page
from app.services.appointment_service import AppointmentService

router = APIRouter(prefix="/appointments", tags=["appointments"])

Viewer = Annotated[User, Depends(require_view(ModuleCode.APPOINTMENTS))]
Manager = Annotated[User, Depends(require_manage(ModuleCode.APPOINTMENTS))]


@router.get("", response_model=Page[AppointmentRead])
def list_appointments(
    db: DbSession,
    current_user: Viewer,
    pagination: PageParams,
    search: Annotated[str | None, Query(max_length=120)] = None,
    practitioner_id: Annotated[int | None, Query()] = None,
    patient_id: Annotated[int | None, Query()] = None,
    appointment_status: Annotated[str | None, Query(alias="status", max_length=20)] = None,
    day: Annotated[date | None, Query()] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> Page[AppointmentRead]:
    items, total = AppointmentService(db).list_appointments(
        term=search,
        practitioner_id=practitioner_id,
        patient_id=patient_id,
        status=appointment_status,
        day=day,
        date_from=date_from,
        date_to=date_to,
        pagination=pagination,
    )
    return Page[AppointmentRead](
        items=[AppointmentRead.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/agenda", response_model=list[AppointmentRead])
def agenda(
    db: DbSession,
    current_user: Viewer,
    day: Annotated[date | None, Query(description="Fecha de la agenda; por defecto hoy")] = None,
    date_from: Annotated[date | None, Query(description="Inicio del rango de días")] = None,
    date_to: Annotated[date | None, Query(description="Fin del rango de días")] = None,
    practitioner_id: Annotated[int | None, Query()] = None,
) -> list[AppointmentRead]:
    """Agenda ordenada por hora, sin paginar.

    Con `day` devuelve la jornada; con `date_from` y `date_to`, el rango que
    pinta la vista de calendario en semana o mes.
    """
    service = AppointmentService(db)
    if date_from and date_to:
        items = service.agenda_for_range(date_from, date_to, practitioner_id)
    else:
        items = service.agenda_for_day(day or today(), practitioner_id)
    return [AppointmentRead.model_validate(item) for item in items]


@router.get("/summary", response_model=AgendaSummary)
def agenda_summary(
    db: DbSession,
    current_user: Viewer,
    day: Annotated[date | None, Query()] = None,
    practitioner_id: Annotated[int | None, Query()] = None,
) -> AgendaSummary:
    return AppointmentService(db).summary_for_day(day or today(), practitioner_id)


@router.get("/availability", response_model=DayAvailability)
def availability(
    db: DbSession,
    current_user: Viewer,
    practitioner_id: Annotated[int, Query()],
    day: Annotated[date | None, Query()] = None,
) -> DayAvailability:
    """Espacios libres del profesional para la fecha indicada."""
    return AppointmentService(db).availability(practitioner_id, day or today())


@router.get("/patient/{patient_id}", response_model=list[AppointmentRead])
def patient_appointments(
    patient_id: int, db: DbSession, current_user: Viewer
) -> list[AppointmentRead]:
    items = AppointmentService(db).history_for_patient(patient_id)
    return [AppointmentRead.model_validate(item) for item in items]


@router.post("", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreate, db: DbSession, current_user: Manager
) -> AppointmentRead:
    return AppointmentRead.model_validate(AppointmentService(db).create(payload, current_user))


@router.get("/{appointment_id}", response_model=AppointmentRead)
def get_appointment(appointment_id: int, db: DbSession, current_user: Viewer) -> AppointmentRead:
    return AppointmentRead.model_validate(AppointmentService(db).get(appointment_id))


@router.put("/{appointment_id}", response_model=AppointmentRead)
def update_appointment(
    appointment_id: int, payload: AppointmentUpdate, db: DbSession, current_user: Manager
) -> AppointmentRead:
    return AppointmentRead.model_validate(AppointmentService(db).update(appointment_id, payload))


@router.patch("/{appointment_id}/status", response_model=AppointmentRead)
def change_appointment_status(
    appointment_id: int,
    payload: AppointmentStatusChange,
    db: DbSession,
    current_user: Manager,
) -> AppointmentRead:
    return AppointmentRead.model_validate(
        AppointmentService(db).change_status(appointment_id, payload.status, payload.cancel_reason)
    )

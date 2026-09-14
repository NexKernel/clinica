from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DbSession, PageParams, require_manage, require_view
from app.core.permissions import ModuleCode
from app.models import User
from app.schemas.common import Page
from app.schemas.reminder import (
    AppointmentReminderPlan,
    ReminderBatch,
    ReminderCreate,
    ReminderPlan,
    ReminderRead,
    ReminderStats,
    ReminderUpdate,
    WhatsAppMessage,
)
from app.services.reminder_service import ReminderService

router = APIRouter(prefix="/reminders", tags=["reminders"])

Viewer = Annotated[User, Depends(require_view(ModuleCode.REMINDERS))]
Manager = Annotated[User, Depends(require_manage(ModuleCode.REMINDERS))]


@router.get("", response_model=Page[ReminderRead])
def list_reminders(
    db: DbSession,
    current_user: Viewer,
    pagination: PageParams,
    patient_id: Annotated[int | None, Query()] = None,
    kind: Annotated[str | None, Query(max_length=16)] = None,
    reminder_status: Annotated[str | None, Query(alias="status", max_length=12)] = None,
    channel: Annotated[str | None, Query(max_length=16)] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> Page[ReminderRead]:
    items, total = ReminderService(db).list_reminders(
        patient_id=patient_id,
        kind=kind,
        status=reminder_status,
        channel=channel,
        date_from=date_from,
        date_to=date_to,
        pagination=pagination,
    )
    return Page[ReminderRead](
        items=[ReminderRead.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/pending", response_model=list[ReminderRead])
def pending_reminders(db: DbSession, current_user: Viewer) -> list[ReminderRead]:
    """Avisos por realizar: vencidos y los programados para hoy."""
    return [ReminderRead.model_validate(item) for item in ReminderService(db).pending()]


@router.get("/stats", response_model=ReminderStats)
def reminder_stats(db: DbSession, current_user: Viewer) -> ReminderStats:
    return ReminderService(db).stats()


@router.post("", response_model=ReminderRead, status_code=status.HTTP_201_CREATED)
def create_reminder(
    payload: ReminderCreate, db: DbSession, current_user: Manager
) -> ReminderRead:
    return ReminderRead.model_validate(ReminderService(db).create(payload, current_user))


@router.post(
    "/from-appointment/{appointment_id}",
    response_model=ReminderBatch,
    status_code=status.HTTP_201_CREATED,
)
def plan_appointment_reminder(
    appointment_id: int,
    payload: AppointmentReminderPlan,
    db: DbSession,
    current_user: Manager,
) -> ReminderBatch:
    """Programa el aviso previo a una cita."""
    items = ReminderService(db).plan_for_appointment(appointment_id, payload, current_user)
    return ReminderBatch(
        created=len(items), items=[ReminderRead.model_validate(item) for item in items]
    )


@router.post(
    "/from-encounter/{encounter_id}",
    response_model=ReminderBatch,
    status_code=status.HTTP_201_CREATED,
)
def plan_medication_reminders(
    encounter_id: int, payload: ReminderPlan, db: DbSession, current_user: Manager
) -> ReminderBatch:
    """Programa las tomas indicadas en las recetas de la atención."""
    items = ReminderService(db).plan_for_encounter(encounter_id, payload, current_user)
    return ReminderBatch(
        created=len(items), items=[ReminderRead.model_validate(item) for item in items]
    )


@router.get("/{reminder_id}", response_model=ReminderRead)
def get_reminder(reminder_id: int, db: DbSession, current_user: Viewer) -> ReminderRead:
    return ReminderRead.model_validate(ReminderService(db).get(reminder_id))


@router.put("/{reminder_id}", response_model=ReminderRead)
def update_reminder(
    reminder_id: int, payload: ReminderUpdate, db: DbSession, current_user: Manager
) -> ReminderRead:
    return ReminderRead.model_validate(ReminderService(db).update(reminder_id, payload))


@router.get("/{reminder_id}/whatsapp", response_model=WhatsAppMessage)
def reminder_whatsapp(
    reminder_id: int, db: DbSession, current_user: Viewer
) -> WhatsAppMessage:
    """Mensaje y enlace listos para enviar desde la cuenta del policlínico."""
    return ReminderService(db).whatsapp_message(reminder_id)


@router.post("/{reminder_id}/sent", response_model=ReminderRead)
def mark_reminder_sent(
    reminder_id: int, db: DbSession, current_user: Manager
) -> ReminderRead:
    return ReminderRead.model_validate(ReminderService(db).mark_sent(reminder_id))


@router.post("/{reminder_id}/cancel", response_model=ReminderRead)
def cancel_reminder(reminder_id: int, db: DbSession, current_user: Manager) -> ReminderRead:
    return ReminderRead.model_validate(ReminderService(db).cancel(reminder_id))

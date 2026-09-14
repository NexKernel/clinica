from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.reminder import ReminderChannel, ReminderKind
from app.schemas.types import LocalDatetime


class ReminderBase(BaseModel):
    patient_id: int
    kind: ReminderKind = ReminderKind.CONTROL
    channel: ReminderChannel = ReminderChannel.WHATSAPP
    title: str = Field(min_length=3, max_length=160)
    message: str = Field(min_length=3, max_length=1000)
    scheduled_for: datetime
    appointment_id: int | None = None
    encounter_id: int | None = None
    prescription_id: int | None = None
    notes: str | None = Field(default=None, max_length=255)

    @field_validator("title", "message", "notes", mode="before")
    @classmethod
    def _clean(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value


class ReminderCreate(ReminderBase):
    """Programación manual de un recordatorio."""


class ReminderUpdate(ReminderBase):
    """Reprogramación o corrección del recordatorio."""


class ReminderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    patient_name: str
    patient_phone: str | None
    appointment_id: int | None
    encounter_id: int | None
    prescription_id: int | None
    kind: str
    kind_label: str
    channel: str
    channel_label: str
    status: str
    status_label: str
    is_pending: bool
    title: str
    message: str
    scheduled_for: LocalDatetime
    sent_at: LocalDatetime | None
    notes: str | None
    created_at: LocalDatetime


class ReminderPlan(BaseModel):
    """Parámetros para generar los recordatorios de un tratamiento."""

    start_at: datetime | None = Field(
        default=None, description="Primera toma; por defecto, la hora actual"
    )
    channel: ReminderChannel = ReminderChannel.WHATSAPP


class AppointmentReminderPlan(BaseModel):
    hours_before: int = Field(default=24, ge=1, le=168)
    channel: ReminderChannel = ReminderChannel.WHATSAPP


class ReminderBatch(BaseModel):
    """Resultado de una generación automática de recordatorios."""

    created: int
    items: list[ReminderRead]


class ReminderStats(BaseModel):
    pending_today: int
    overdue: int
    sent_today: int
    upcoming_week: int


class WhatsAppMessage(BaseModel):
    reminder_id: int
    phone: str | None
    message: str
    whatsapp_url: str | None

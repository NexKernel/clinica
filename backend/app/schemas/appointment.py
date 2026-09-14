from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.appointment import AppointmentStatus
from app.schemas.patient import PatientSummary
from app.schemas.types import LocalDatetime


class AppointmentBase(BaseModel):
    patient_id: int
    practitioner_id: int
    service_id: int | None = None
    scheduled_at: datetime
    duration_minutes: int | None = Field(default=None, ge=5, le=240)
    reason: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("reason", "notes", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = " ".join(value.split())
            return cleaned or None
        return value


class AppointmentCreate(AppointmentBase):
    """Programación de una cita."""


class AppointmentUpdate(AppointmentBase):
    """Reprogramación o corrección de datos de la cita."""


class AppointmentStatusChange(BaseModel):
    status: AppointmentStatus
    cancel_reason: str | None = Field(default=None, max_length=255)


class AppointmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    practitioner_id: int
    service_id: int | None
    scheduled_at: LocalDatetime
    duration_minutes: int
    status: str
    status_label: str
    reason: str | None
    notes: str | None
    cancel_reason: str | None
    is_closed: bool
    patient_name: str
    practitioner_name: str
    specialty_name: str | None
    service_name: str | None
    patient: PatientSummary
    created_at: LocalDatetime


class AppointmentSlot(BaseModel):
    """Espacio de la agenda de un profesional en una fecha."""

    start: LocalDatetime
    end: LocalDatetime
    available: bool
    appointment_id: int | None = None
    patient_name: str | None = None
    status: str | None = None


class DayAvailability(BaseModel):
    practitioner_id: int
    practitioner_name: str
    day: date
    slot_minutes: int
    working: bool
    slots: list[AppointmentSlot]


class AgendaSummary(BaseModel):
    """Indicadores de la agenda para el día consultado."""

    day: date
    total: int
    scheduled: int
    attended: int
    cancelled: int
    no_show: int


class ScheduleBlock(BaseModel):
    start_time: time
    end_time: time

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.patient import PatientSummary
from app.schemas.types import LocalDatetime


class CredEntryWrite(BaseModel):
    """Registro de una prestación aplicada."""

    item_code: str = Field(min_length=2, max_length=32)
    performed_on: date
    result: str | None = Field(default=None, max_length=160)
    notes: str | None = Field(default=None, max_length=1000)
    practitioner_id: int | None = None

    @field_validator("result", "notes", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = " ".join(value.split())
            return cleaned or None
        return value


class CredEntryCreate(CredEntryWrite):
    patient_id: int


class CredEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    item_code: str
    sequence: int
    performed_on: date
    result: str | None
    notes: str | None
    practitioner_id: int | None
    practitioner_name: str | None
    created_at: LocalDatetime


class CredSlot(BaseModel):
    """Una casilla del carné: lo que toca y, si ya se dio, cuándo."""

    item_code: str
    group: str
    label: str
    dose: str
    due_month: int | None
    status: str
    status_label: str
    records_result: bool
    entries: list[CredEntryRead] = Field(default_factory=list)


class CredSection(BaseModel):
    """Una de las rejillas del carné."""

    kind: str
    label: str
    slots: list[CredSlot]
    applied: int
    overdue: int


class CredCard(BaseModel):
    """Carné completo de un niño: el calendario cruzado con lo aplicado."""

    patient: PatientSummary
    age_months: int | None
    age_label: str
    in_program: bool
    sections: list[CredSection]
    applied: int
    overdue: int
    pending: int


class CredSheet(BaseModel):
    """Carné listo para imprimir y entregar."""

    title: str
    number: str
    html: str


class CredCatalogItem(BaseModel):
    """Prestación ofrecida al registrar, ya marcada si no admite repetición."""

    code: str
    kind: str
    kind_label: str
    group: str
    label: str
    dose: str
    due_month: int | None
    records_result: bool
    repeatable: bool
    already_applied: bool

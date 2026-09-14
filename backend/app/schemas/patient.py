from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.datetime import today
from app.models.patient import DOCUMENT_CATALOG, DocumentType, Sex
from app.schemas.types import LocalDatetime

DIGITS_ONLY = {DocumentType.DNI, DocumentType.RUC}


class PatientBase(BaseModel):
    document_type: DocumentType = DocumentType.DNI
    document_number: str | None = Field(default=None, max_length=20)
    first_name: str = Field(min_length=2, max_length=80)
    last_name_paternal: str = Field(min_length=2, max_length=80)
    last_name_maternal: str | None = Field(default=None, max_length=80)
    birth_date: date | None = None
    sex: Sex | None = None

    phone: str | None = Field(default=None, max_length=40)
    whatsapp: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = Field(default=None, max_length=160)
    address: str | None = Field(default=None, max_length=255)
    district: str | None = Field(default=None, max_length=80)
    province: str | None = Field(default=None, max_length=80)
    department: str | None = Field(default=None, max_length=80)

    emergency_contact: str | None = Field(default=None, max_length=160)
    emergency_phone: str | None = Field(default=None, max_length=40)

    blood_type: str | None = Field(default=None, max_length=6)
    insurance: str | None = Field(default=None, max_length=80)
    allergies: str | None = Field(default=None, max_length=1000)
    personal_history: str | None = Field(default=None, max_length=2000)
    family_history: str | None = Field(default=None, max_length=2000)
    surgical_history: str | None = Field(default=None, max_length=2000)
    current_medication: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)

    is_active: bool = True

    @field_validator("*", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = " ".join(value.split())
            return cleaned or None
        return value

    @field_validator("first_name", "last_name_paternal", "last_name_maternal")
    @classmethod
    def _titleize(cls, value: str | None) -> str | None:
        return value.upper() if value else value

    @field_validator("birth_date")
    @classmethod
    def _check_birth_date(cls, value: date | None) -> date | None:
        if value is None:
            return None
        if value > today():
            raise ValueError("La fecha de nacimiento no puede ser futura")
        if value.year < 1900:
            raise ValueError("Verifique la fecha de nacimiento")
        return value

    @model_validator(mode="after")
    def _check_document(self) -> "PatientBase":
        if self.document_type is DocumentType.SIN_DOCUMENTO:
            self.document_number = None
            return self
        if not self.document_number:
            raise ValueError("Ingrese el número de documento")
        if self.document_type in DIGITS_ONLY and not self.document_number.isdigit():
            raise ValueError("El número de documento debe contener solo dígitos")
        _, expected = DOCUMENT_CATALOG[self.document_type]
        if expected is not None and len(self.document_number) != expected:
            raise ValueError(f"El documento debe tener {expected} dígitos")
        return self


class PatientCreate(PatientBase):
    """Alta de paciente desde recepción."""


class PatientUpdate(PatientBase):
    """Actualización completa de la ficha del paciente."""


class PatientRead(PatientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: str
    history_number: str
    full_name: str
    display_name: str
    age: int | None
    sex_label: str | None
    document_label: str
    has_alerts: bool
    created_at: LocalDatetime
    updated_at: LocalDatetime


class PatientSummary(BaseModel):
    """Ficha resumida para selectores y listados de otros módulos."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: str
    history_number: str
    full_name: str
    document_type: str
    document_number: str | None
    age: int | None
    sex: str | None
    phone: str | None
    whatsapp: str | None
    has_alerts: bool


class PatientStats(BaseModel):
    """Indicadores del padrón de pacientes."""

    total: int
    active: int
    registered_today: int
    registered_this_month: int

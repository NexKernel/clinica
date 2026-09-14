from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.study import StudyStatus, StudyType
from app.schemas.patient import PatientSummary
from app.schemas.types import LocalDatetime


class AttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    content_type: str
    size_bytes: int
    size_label: str
    is_image: bool
    description: str | None
    created_at: LocalDatetime


class StudyBase(BaseModel):
    patient_id: int
    encounter_id: int | None = None
    requested_by_id: int | None = None
    service_id: int | None = None
    study_type: StudyType
    name: str = Field(min_length=3, max_length=160)
    clinical_notes: str | None = Field(default=None, max_length=2000)

    @field_validator("name", "clinical_notes", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = " ".join(value.split())
            return cleaned or None
        return value


class StudyCreate(StudyBase):
    """Solicitud de un examen o estudio."""

    requested_at: datetime | None = None


class StudyUpdate(StudyBase):
    """Corrección de los datos de la solicitud."""


class StudyResultWrite(BaseModel):
    """Registro del resultado o informe del estudio (cláusula 2.4)."""

    result_summary: str | None = Field(default=None, max_length=255)
    report: str | None = Field(default=None, max_length=8000)
    performed_by: str | None = Field(default=None, max_length=160)
    performed_at: datetime | None = None
    complete: bool = Field(default=True, description="Marca el estudio como completado")


class StudyStatusChange(BaseModel):
    status: StudyStatus


class StudyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    encounter_id: int | None
    requested_by_id: int | None
    service_id: int | None
    study_type: str
    type_label: str
    name: str
    status: str
    status_label: str
    requested_at: LocalDatetime
    performed_at: LocalDatetime | None
    performed_by: str | None
    clinical_notes: str | None
    result_summary: str | None
    report: str | None
    has_result: bool
    is_completed: bool
    attachment_count: int
    shared_at: LocalDatetime | None
    share_expires_at: LocalDatetime | None
    patient_name: str
    requested_by_name: str | None
    attachments: list[AttachmentRead]
    patient: PatientSummary
    created_at: LocalDatetime


class StudyListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    patient_name: str
    study_type: str
    type_label: str
    name: str
    status: str
    status_label: str
    requested_at: LocalDatetime
    performed_at: LocalDatetime | None
    result_summary: str | None
    attachment_count: int
    has_result: bool
    shared_at: LocalDatetime | None


class ShareLink(BaseModel):
    """Enlace de consulta del resultado y mensaje listo para WhatsApp."""

    study_id: int
    url: str
    whatsapp_url: str | None
    message: str
    expires_at: LocalDatetime


class SharedAttachment(BaseModel):
    id: int
    filename: str
    content_type: str
    size_label: str
    is_image: bool
    url: str


class SharedStudy(BaseModel):
    """Vista pública del resultado, accesible solo con el enlace vigente."""

    clinic_name: str
    clinic_logo_url: str | None
    patient_name: str
    study_name: str
    type_label: str
    performed_at: LocalDatetime | None
    result_summary: str | None
    report: str | None
    performed_by: str | None
    attachments: list[SharedAttachment]
    expires_at: LocalDatetime

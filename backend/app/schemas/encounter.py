from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.encounter import DiagnosisKind
from app.schemas.patient import PatientSummary
from app.schemas.types import LocalDatetime


class DiagnosisWrite(BaseModel):
    code: str | None = Field(default=None, max_length=12, description="Código CIE-10")
    description: str = Field(min_length=3, max_length=255)
    kind: DiagnosisKind = DiagnosisKind.DEFINITIVO

    @field_validator("code")
    @classmethod
    def _upper_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None


class DiagnosisRead(DiagnosisWrite):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind_label: str
    summary: str


class PrescriptionWrite(BaseModel):
    product_id: int | None = None
    medication: str = Field(min_length=2, max_length=160)
    dose: str | None = Field(default=None, max_length=80)
    frequency_hours: int | None = Field(default=None, ge=1, le=72)
    frequency_text: str | None = Field(default=None, max_length=80)
    duration_days: int | None = Field(default=None, ge=1, le=365)
    quantity: int | None = Field(default=None, ge=1, le=1000)
    instructions: str | None = Field(default=None, max_length=1000)


class PrescriptionRead(PrescriptionWrite):
    model_config = ConfigDict(from_attributes=True)

    id: int
    schedule_label: str


class VitalSigns(BaseModel):
    systolic_pressure: int | None = Field(default=None, ge=50, le=300)
    diastolic_pressure: int | None = Field(default=None, ge=30, le=200)
    heart_rate: int | None = Field(default=None, ge=20, le=250)
    respiratory_rate: int | None = Field(default=None, ge=5, le=90)
    temperature: Decimal | None = Field(default=None, ge=30, le=45, max_digits=4, decimal_places=1)
    oxygen_saturation: int | None = Field(default=None, ge=40, le=100)
    weight_kg: Decimal | None = Field(default=None, gt=0, le=400, max_digits=5, decimal_places=2)
    height_cm: Decimal | None = Field(default=None, gt=0, le=250, max_digits=5, decimal_places=1)


class EncounterBase(VitalSigns):
    service_id: int | None = None
    chief_complaint: str | None = Field(default=None, max_length=255)
    current_illness: str | None = Field(default=None, max_length=4000)
    physical_exam: str | None = Field(default=None, max_length=4000)
    treatment_plan: str | None = Field(default=None, max_length=4000)
    indications: str | None = Field(default=None, max_length=4000)
    observations: str | None = Field(default=None, max_length=2000)

    @field_validator(
        "chief_complaint",
        "current_illness",
        "physical_exam",
        "treatment_plan",
        "indications",
        "observations",
        mode="before",
    )
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None
        return value


class EncounterCreate(EncounterBase):
    """Inicio de una atención médica."""

    patient_id: int
    practitioner_id: int
    appointment_id: int | None = None
    started_at: datetime | None = None
    diagnoses: list[DiagnosisWrite] = Field(default_factory=list)
    prescriptions: list[PrescriptionWrite] = Field(default_factory=list)


class EncounterUpdate(EncounterBase):
    """Actualización del contenido clínico mientras la atención está en curso."""

    diagnoses: list[DiagnosisWrite] | None = None
    prescriptions: list[PrescriptionWrite] | None = None


class EncounterRead(EncounterBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    practitioner_id: int
    appointment_id: int | None
    started_at: LocalDatetime
    finished_at: LocalDatetime | None
    status: str
    status_label: str
    is_editable: bool
    patient_name: str
    practitioner_name: str
    specialty_name: str | None
    blood_pressure: str | None
    bmi: float | None
    main_diagnosis: str | None
    diagnoses: list[DiagnosisRead]
    prescriptions: list[PrescriptionRead]
    patient: PatientSummary
    created_at: LocalDatetime


class EncounterListItem(BaseModel):
    """Fila del listado de atenciones y del historial del paciente."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    patient_name: str
    practitioner_name: str
    specialty_name: str | None
    started_at: LocalDatetime
    finished_at: LocalDatetime | None
    status: str
    status_label: str
    chief_complaint: str | None
    main_diagnosis: str | None


class MedicalRecord(BaseModel):
    """Historia clínica consolidada de un paciente (cláusula 2.2)."""

    patient: PatientSummary
    total_encounters: int
    last_encounter_at: LocalDatetime | None
    encounters: list[EncounterListItem]

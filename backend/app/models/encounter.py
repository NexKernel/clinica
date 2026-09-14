from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.appointment import Appointment
from app.models.catalog import MedicalService
from app.models.inventory import Product
from app.models.patient import Patient
from app.models.practitioner import Practitioner


class EncounterStatus(StrEnum):
    EN_CURSO = "EN_CURSO"
    FINALIZADA = "FINALIZADA"
    ANULADA = "ANULADA"


ENCOUNTER_STATUS_LABELS: dict[str, str] = {
    EncounterStatus.EN_CURSO.value: "En curso",
    EncounterStatus.FINALIZADA.value: "Finalizada",
    EncounterStatus.ANULADA.value: "Anulada",
}


class DiagnosisKind(StrEnum):
    PRESUNTIVO = "PRESUNTIVO"
    DEFINITIVO = "DEFINITIVO"
    REPETIDO = "REPETIDO"


DIAGNOSIS_KIND_LABELS: dict[str, str] = {
    DiagnosisKind.PRESUNTIVO.value: "Presuntivo",
    DiagnosisKind.DEFINITIVO.value: "Definitivo",
    DiagnosisKind.REPETIDO.value: "Repetido",
}


class Encounter(Base, TimestampMixin):
    """Atención médica registrada por el profesional (cláusula 2.3)."""

    __tablename__ = "encounters"
    __table_args__ = (Index("ix_encounters_patient_date", "patient_id", "started_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    practitioner_id: Mapped[int] = mapped_column(ForeignKey("practitioners.id"), nullable=False)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"), unique=True)
    service_id: Mapped[int | None] = mapped_column(ForeignKey("medical_services.id"))

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(
        String(16), default=EncounterStatus.EN_CURSO.value, nullable=False, index=True
    )

    # Anamnesis y examen
    chief_complaint: Mapped[str | None] = mapped_column(String(255))
    current_illness: Mapped[str | None] = mapped_column(Text)
    physical_exam: Mapped[str | None] = mapped_column(Text)
    treatment_plan: Mapped[str | None] = mapped_column(Text)
    indications: Mapped[str | None] = mapped_column(Text)
    observations: Mapped[str | None] = mapped_column(Text)

    # Signos vitales
    systolic_pressure: Mapped[int | None] = mapped_column(Integer)
    diastolic_pressure: Mapped[int | None] = mapped_column(Integer)
    heart_rate: Mapped[int | None] = mapped_column(Integer)
    respiratory_rate: Mapped[int | None] = mapped_column(Integer)
    temperature: Mapped[Decimal | None] = mapped_column(Numeric(4, 1))
    oxygen_saturation: Mapped[int | None] = mapped_column(Integer)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))

    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    patient: Mapped[Patient] = relationship(lazy="joined")
    practitioner: Mapped[Practitioner] = relationship(lazy="joined")
    appointment: Mapped[Appointment | None] = relationship()
    service: Mapped[MedicalService | None] = relationship(lazy="joined")
    diagnoses: Mapped[list["EncounterDiagnosis"]] = relationship(
        back_populates="encounter", cascade="all, delete-orphan", lazy="selectin", order_by="EncounterDiagnosis.id"
    )
    prescriptions: Mapped[list["Prescription"]] = relationship(
        back_populates="encounter", cascade="all, delete-orphan", lazy="selectin", order_by="Prescription.id"
    )

    @property
    def status_label(self) -> str:
        return ENCOUNTER_STATUS_LABELS.get(self.status, self.status)

    @property
    def patient_name(self) -> str:
        return self.patient.full_name

    @property
    def practitioner_name(self) -> str:
        return self.practitioner.full_name

    @property
    def specialty_name(self) -> str | None:
        return self.practitioner.specialty_name

    @property
    def blood_pressure(self) -> str | None:
        if self.systolic_pressure and self.diastolic_pressure:
            return f"{self.systolic_pressure}/{self.diastolic_pressure}"
        return None

    @property
    def bmi(self) -> float | None:
        """Índice de masa corporal, calculado a partir de peso y talla."""
        if not self.weight_kg or not self.height_cm or self.height_cm <= 0:
            return None
        meters = float(self.height_cm) / 100
        return round(float(self.weight_kg) / (meters * meters), 1)

    @property
    def main_diagnosis(self) -> str | None:
        return self.diagnoses[0].summary if self.diagnoses else None

    @property
    def is_editable(self) -> bool:
        return self.status == EncounterStatus.EN_CURSO.value


class EncounterDiagnosis(Base, TimestampMixin):
    """Diagnóstico registrado en la atención (CIE-10 o descripción libre)."""

    __tablename__ = "encounter_diagnoses"

    id: Mapped[int] = mapped_column(primary_key=True)
    encounter_id: Mapped[int] = mapped_column(
        ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str | None] = mapped_column(String(12), index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(16), default=DiagnosisKind.DEFINITIVO.value, nullable=False)

    encounter: Mapped[Encounter] = relationship(back_populates="diagnoses")

    @property
    def kind_label(self) -> str:
        return DIAGNOSIS_KIND_LABELS.get(self.kind, self.kind)

    @property
    def summary(self) -> str:
        return f"{self.code} — {self.description}" if self.code else self.description


class Prescription(Base, TimestampMixin):
    """Medicamento indicado en la atención (cláusulas 2.3 y 2.5)."""

    __tablename__ = "prescriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    encounter_id: Mapped[int] = mapped_column(
        ForeignKey("encounters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    medication: Mapped[str] = mapped_column(String(160), nullable=False)
    dose: Mapped[str | None] = mapped_column(String(80))
    frequency_hours: Mapped[int | None] = mapped_column(Integer)
    frequency_text: Mapped[str | None] = mapped_column(String(80))
    duration_days: Mapped[int | None] = mapped_column(Integer)
    quantity: Mapped[int | None] = mapped_column(Integer)
    instructions: Mapped[str | None] = mapped_column(Text)

    encounter: Mapped[Encounter] = relationship(back_populates="prescriptions")
    product: Mapped[Product | None] = relationship(lazy="joined")

    @property
    def schedule_label(self) -> str:
        """Resumen legible: «500 mg cada 8 h por 5 días»."""
        parts: list[str] = []
        if self.dose:
            parts.append(self.dose)
        if self.frequency_hours:
            parts.append(f"cada {self.frequency_hours} h")
        elif self.frequency_text:
            parts.append(self.frequency_text)
        if self.duration_days:
            parts.append(f"por {self.duration_days} día{'s' if self.duration_days != 1 else ''}")
        return " ".join(parts)

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.catalog import MedicalService
from app.models.patient import Patient
from app.models.practitioner import Practitioner


class AppointmentStatus(StrEnum):
    PROGRAMADA = "PROGRAMADA"
    CONFIRMADA = "CONFIRMADA"
    EN_ATENCION = "EN_ATENCION"
    ATENDIDA = "ATENDIDA"
    CANCELADA = "CANCELADA"
    NO_ASISTIO = "NO_ASISTIO"


APPOINTMENT_STATUS_LABELS: dict[str, str] = {
    AppointmentStatus.PROGRAMADA.value: "Programada",
    AppointmentStatus.CONFIRMADA.value: "Confirmada",
    AppointmentStatus.EN_ATENCION.value: "En atención",
    AppointmentStatus.ATENDIDA.value: "Atendida",
    AppointmentStatus.CANCELADA.value: "Cancelada",
    AppointmentStatus.NO_ASISTIO.value: "No asistió",
}

# Estados que ocupan un espacio en la agenda del profesional.
BLOCKING_STATUSES: tuple[str, ...] = (
    AppointmentStatus.PROGRAMADA.value,
    AppointmentStatus.CONFIRMADA.value,
    AppointmentStatus.EN_ATENCION.value,
    AppointmentStatus.ATENDIDA.value,
)

CLOSED_STATUSES: tuple[str, ...] = (
    AppointmentStatus.ATENDIDA.value,
    AppointmentStatus.CANCELADA.value,
    AppointmentStatus.NO_ASISTIO.value,
)


class Appointment(Base, TimestampMixin):
    """Cita programada para un paciente con un profesional (cláusula 2.1)."""

    __tablename__ = "appointments"
    __table_args__ = (
        Index("ix_appointments_agenda", "practitioner_id", "scheduled_at"),
        Index("ix_appointments_patient_date", "patient_id", "scheduled_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    practitioner_id: Mapped[int] = mapped_column(ForeignKey("practitioners.id"), nullable=False)
    service_id: Mapped[int | None] = mapped_column(ForeignKey("medical_services.id"))

    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), default=AppointmentStatus.PROGRAMADA.value, nullable=False, index=True
    )

    reason: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    cancel_reason: Mapped[str | None] = mapped_column(String(255))

    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    patient: Mapped[Patient] = relationship(lazy="joined")
    practitioner: Mapped[Practitioner] = relationship(lazy="joined")
    service: Mapped[MedicalService | None] = relationship(lazy="joined")

    @property
    def status_label(self) -> str:
        return APPOINTMENT_STATUS_LABELS.get(self.status, self.status)

    @property
    def is_closed(self) -> bool:
        return self.status in CLOSED_STATUSES

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
    def service_name(self) -> str | None:
        return self.service.name if self.service else None

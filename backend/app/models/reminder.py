from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.patient import Patient


class ReminderKind(StrEnum):
    MEDICAMENTO = "MEDICAMENTO"
    CITA = "CITA"
    CONTROL = "CONTROL"
    RESULTADO = "RESULTADO"


REMINDER_KIND_LABELS: dict[str, str] = {
    ReminderKind.MEDICAMENTO.value: "Toma de medicamento",
    ReminderKind.CITA.value: "Recordatorio de cita",
    ReminderKind.CONTROL.value: "Control médico",
    ReminderKind.RESULTADO.value: "Entrega de resultado",
}


class ReminderChannel(StrEnum):
    WHATSAPP = "WHATSAPP"
    LLAMADA = "LLAMADA"
    SMS = "SMS"
    PRESENCIAL = "PRESENCIAL"


REMINDER_CHANNEL_LABELS: dict[str, str] = {
    ReminderChannel.WHATSAPP.value: "WhatsApp",
    ReminderChannel.LLAMADA.value: "Llamada telefónica",
    ReminderChannel.SMS.value: "Mensaje de texto",
    ReminderChannel.PRESENCIAL.value: "Aviso presencial",
}


class ReminderStatus(StrEnum):
    PENDIENTE = "PENDIENTE"
    ENVIADO = "ENVIADO"
    CANCELADO = "CANCELADO"


REMINDER_STATUS_LABELS: dict[str, str] = {
    ReminderStatus.PENDIENTE.value: "Pendiente",
    ReminderStatus.ENVIADO.value: "Enviado",
    ReminderStatus.CANCELADO.value: "Cancelado",
}


class Reminder(Base, TimestampMixin):
    """Recordatorio programado para el paciente (cláusula 2.5).

    El sistema programa y controla el estado del aviso; el envío efectivo se
    realiza por el canal elegido (WhatsApp, llamada) desde el mismo módulo.
    """

    __tablename__ = "reminders"
    __table_args__ = (
        Index("ix_reminders_pending", "status", "scheduled_for"),
        Index("ix_reminders_patient", "patient_id", "scheduled_for"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id", ondelete="SET NULL"))
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounters.id", ondelete="SET NULL"))
    prescription_id: Mapped[int | None] = mapped_column(
        ForeignKey("prescriptions.id", ondelete="CASCADE")
    )

    kind: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(
        String(16), default=ReminderChannel.WHATSAPP.value, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(12), default=ReminderStatus.PENDIENTE.value, nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(160), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(String(255))

    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    patient: Mapped[Patient] = relationship(lazy="joined")

    @property
    def kind_label(self) -> str:
        return REMINDER_KIND_LABELS.get(self.kind, self.kind)

    @property
    def channel_label(self) -> str:
        return REMINDER_CHANNEL_LABELS.get(self.channel, self.channel)

    @property
    def status_label(self) -> str:
        return REMINDER_STATUS_LABELS.get(self.status, self.status)

    @property
    def patient_name(self) -> str:
        return self.patient.full_name

    @property
    def patient_phone(self) -> str | None:
        return self.patient.whatsapp or self.patient.phone

    @property
    def is_pending(self) -> bool:
        return self.status == ReminderStatus.PENDIENTE.value

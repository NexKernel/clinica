from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.models.practitioner import Practitioner


class StudyType(StrEnum):
    LABORATORIO = "LABORATORIO"
    RAYOS_X = "RAYOS_X"
    ECOGRAFIA = "ECOGRAFIA"
    OPTOMETRIA = "OPTOMETRIA"
    OTRO = "OTRO"


STUDY_TYPE_LABELS: dict[str, str] = {
    StudyType.LABORATORIO.value: "Laboratorio",
    StudyType.RAYOS_X.value: "Rayos X",
    StudyType.ECOGRAFIA.value: "Ecografía",
    StudyType.OPTOMETRIA.value: "Optometría",
    StudyType.OTRO.value: "Otro estudio",
}


class StudyStatus(StrEnum):
    SOLICITADO = "SOLICITADO"
    EN_PROCESO = "EN_PROCESO"
    COMPLETADO = "COMPLETADO"
    ANULADO = "ANULADO"


STUDY_STATUS_LABELS: dict[str, str] = {
    StudyStatus.SOLICITADO.value: "Solicitado",
    StudyStatus.EN_PROCESO.value: "En proceso",
    StudyStatus.COMPLETADO.value: "Completado",
    StudyStatus.ANULADO.value: "Anulado",
}


class ClinicalStudy(Base, TimestampMixin):
    """Examen de laboratorio, estudio de Rayos X u otro apoyo al diagnóstico.

    Cubre la cláusula 2.4: registro de la solicitud, del resultado o informe,
    de los archivos asociados y del enlace de envío al paciente.
    """

    __tablename__ = "clinical_studies"
    __table_args__ = (Index("ix_studies_patient_date", "patient_id", "requested_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounters.id"))
    requested_by_id: Mapped[int | None] = mapped_column(ForeignKey("practitioners.id"))
    service_id: Mapped[int | None] = mapped_column(ForeignKey("medical_services.id"))

    study_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default=StudyStatus.SOLICITADO.value, nullable=False, index=True
    )

    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    performed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    performed_by: Mapped[str | None] = mapped_column(String(160))

    clinical_notes: Mapped[str | None] = mapped_column(Text)
    result_summary: Mapped[str | None] = mapped_column(String(255))
    report: Mapped[str | None] = mapped_column(Text)

    # Envío al paciente (cláusula 2.4: enlace por WhatsApp)
    share_token: Mapped[str | None] = mapped_column(String(48), unique=True, index=True)
    share_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    patient: Mapped[Patient] = relationship(lazy="joined")
    encounter: Mapped[Encounter | None] = relationship()
    requested_by: Mapped[Practitioner | None] = relationship(lazy="joined")
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="study",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Attachment.id",
    )

    @property
    def type_label(self) -> str:
        return STUDY_TYPE_LABELS.get(self.study_type, self.study_type)

    @property
    def status_label(self) -> str:
        return STUDY_STATUS_LABELS.get(self.status, self.status)

    @property
    def patient_name(self) -> str:
        return self.patient.full_name

    @property
    def requested_by_name(self) -> str | None:
        return self.requested_by.full_name if self.requested_by else None

    @property
    def attachment_count(self) -> int:
        return len(self.attachments)

    @property
    def is_completed(self) -> bool:
        return self.status == StudyStatus.COMPLETADO.value

    @property
    def has_result(self) -> bool:
        return bool(self.report or self.result_summary or self.attachments)


class Attachment(Base, TimestampMixin):
    """Archivo asociado a un estudio o a una atención del paciente."""

    __tablename__ = "attachments"
    __table_args__ = (Index("ix_attachments_patient", "patient_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    study_id: Mapped[int | None] = mapped_column(ForeignKey("clinical_studies.id", ondelete="CASCADE"))
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounters.id", ondelete="CASCADE"))

    filename: Mapped[str] = mapped_column(String(200), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))

    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    study: Mapped[ClinicalStudy | None] = relationship(back_populates="attachments")

    @property
    def size_label(self) -> str:
        size = float(self.size_bytes)
        for unit in ("B", "KB", "MB"):
            if size < 1024 or unit == "MB":
                return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} MB"

    @property
    def is_image(self) -> bool:
        return self.content_type.startswith("image/")

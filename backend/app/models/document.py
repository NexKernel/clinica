from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.encounter import Encounter
from app.models.patient import Patient
from app.models.practitioner import Practitioner
from app.models.study import ClinicalStudy


class DocumentFamily(StrEnum):
    """Familias del formulario en papel, con requisitos distintos.

    Los informes y las fichas capturan datos clínicos consultables; los
    consentimientos y actas valen por su texto, que debe quedar inmutable.
    """

    INFORME = "INFORME"
    FICHA = "FICHA"
    CONSENTIMIENTO = "CONSENTIMIENTO"
    ADMINISTRATIVO = "ADMINISTRATIVO"


DOCUMENT_FAMILY_LABELS: dict[str, str] = {
    DocumentFamily.INFORME.value: "Informe de resultado",
    DocumentFamily.FICHA.value: "Ficha clínica",
    DocumentFamily.CONSENTIMIENTO.value: "Consentimiento y declaración",
    DocumentFamily.ADMINISTRATIVO.value: "Documento administrativo",
}


class DocumentStatus(StrEnum):
    BORRADOR = "BORRADOR"
    EMITIDO = "EMITIDO"
    ANULADO = "ANULADO"


DOCUMENT_STATUS_LABELS: dict[str, str] = {
    DocumentStatus.BORRADOR.value: "Borrador",
    DocumentStatus.EMITIDO.value: "Emitido",
    DocumentStatus.ANULADO.value: "Anulado",
}


class DocumentTemplate(Base, TimestampMixin):
    """Plantilla del catálogo: el formato en papel, expresado como HTML.

    Se versiona por código: al cambiar el texto de un consentimiento se agrega
    una versión nueva y la anterior se desactiva, de modo que los documentos ya
    emitidos sigan explicando con qué texto se firmaron.
    """

    __tablename__ = "document_templates"
    __table_args__ = (
        UniqueConstraint("code", "version", name="uq_document_template_version"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    family: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))

    body: Mapped[str] = mapped_column(Text, nullable=False)
    # Definición de los campos que captura el usuario. La estructura de cada
    # entrada está documentada en app/db/document_seeds.py.
    fields: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    requires_signature: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Tipo de estudio que sugiere al vincular el documento (solo informes).
    study_type: Mapped[str | None] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def family_label(self) -> str:
        return DOCUMENT_FAMILY_LABELS.get(self.family, self.family)

    @property
    def field_count(self) -> int:
        return len(self.fields or [])

    @property
    def defaults(self) -> dict[str, Any]:
        """Valores sugeridos: el hallazgo normal que trae el formato impreso."""
        return {
            field["key"]: field["default"]
            for field in (self.fields or [])
            if field.get("default") is not None
        }


class ClinicalDocument(Base, TimestampMixin):
    """Documento emitido a un paciente a partir de una plantilla.

    Mientras es borrador se rearma en cada consulta; al emitirse se congela el
    HTML resultante en `content`, que es lo que vale como constancia. Anular no
    borra: conserva el documento y su motivo.
    """

    __tablename__ = "clinical_documents"
    __table_args__ = (Index("ix_documents_patient_date", "patient_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False)
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounters.id"))
    study_id: Mapped[int | None] = mapped_column(ForeignKey("clinical_studies.id"))
    practitioner_id: Mapped[int | None] = mapped_column(ForeignKey("practitioners.id"))

    template_id: Mapped[int] = mapped_column(ForeignKey("document_templates.id"), nullable=False)
    # Código y versión copiados: identifican el formato aunque la plantilla se
    # desactive o el catálogo cambie más adelante.
    template_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    template_version: Mapped[int] = mapped_column(Integer, nullable=False)

    family: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default=DocumentStatus.BORRADOR.value, nullable=False, index=True
    )

    # Datos capturados. El servicio siempre reasigna el diccionario completo:
    # SQLAlchemy no detecta mutaciones en sitio sobre una columna JSON.
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    content: Mapped[str | None] = mapped_column(Text)

    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    issued_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    voided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    void_reason: Mapped[str | None] = mapped_column(String(255))

    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    patient: Mapped[Patient] = relationship(lazy="joined")
    template: Mapped[DocumentTemplate] = relationship(lazy="joined")
    practitioner: Mapped[Practitioner | None] = relationship(lazy="joined")
    encounter: Mapped[Encounter | None] = relationship()
    study: Mapped[ClinicalStudy | None] = relationship()

    @property
    def number(self) -> str:
        """Referencia legible del documento: «CI-VIH-00042»."""
        return f"{self.template_code}-{self.id:05d}"

    @property
    def family_label(self) -> str:
        return DOCUMENT_FAMILY_LABELS.get(self.family, self.family)

    @property
    def status_label(self) -> str:
        return DOCUMENT_STATUS_LABELS.get(self.status, self.status)

    @property
    def patient_name(self) -> str:
        return self.patient.full_name

    @property
    def practitioner_name(self) -> str | None:
        return self.practitioner.full_name if self.practitioner else None

    @property
    def is_draft(self) -> bool:
        return self.status == DocumentStatus.BORRADOR.value

    @property
    def is_issued(self) -> bool:
        return self.status == DocumentStatus.EMITIDO.value

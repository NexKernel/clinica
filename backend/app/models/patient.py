from datetime import date
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import Boolean, Date, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.datetime import today
from app.db.base import Base, TimestampMixin


class DocumentType(StrEnum):
    DNI = "DNI"
    CE = "CE"
    PASAPORTE = "PASAPORTE"
    RUC = "RUC"
    SIN_DOCUMENTO = "SIN_DOCUMENTO"


class Sex(StrEnum):
    MASCULINO = "M"
    FEMENINO = "F"


# Documento -> (nombre visible, longitud exacta esperada; None = libre)
DOCUMENT_CATALOG: dict[DocumentType, tuple[str, int | None]] = {
    DocumentType.DNI: ("DNI", 8),
    DocumentType.CE: ("Carné de extranjería", None),
    DocumentType.PASAPORTE: ("Pasaporte", None),
    DocumentType.RUC: ("RUC", 11),
    DocumentType.SIN_DOCUMENTO: ("Sin documento", None),
}

SEX_LABELS: dict[str, str] = {
    Sex.MASCULINO.value: "Masculino",
    Sex.FEMENINO.value: "Femenino",
}

# Estados civiles que admite la hoja de filiación. Se guarda la etiqueta misma,
# así que la lista solo sirve para ofrecerlos y para rechazar un valor inventado.
MARITAL_STATUSES: tuple[str, ...] = (
    "Soltero(a)",
    "Casado(a)",
    "Conviviente",
    "Divorciado(a)",
    "Viudo(a)",
)


def new_public_id() -> str:
    """UUID4 en hexadecimal, sin guiones, para las rutas del frontend."""
    return uuid4().hex


class Patient(Base, TimestampMixin):
    """Paciente del policlínico y sus antecedentes clínicos básicos."""

    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint("document_type", "document_number", name="uq_patient_document"),
        Index("ix_patients_last_names", "last_name_paternal", "last_name_maternal"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # Identificador opaco para las URLs: el id correlativo no sale del servidor
    # hacia la barra de direcciones, de modo que una ficha no se descubre
    # tanteando /pacientes/1, /pacientes/2...
    public_id: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False, default=new_public_id
    )
    history_number: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)

    # Identificación
    document_type: Mapped[str] = mapped_column(String(20), default=DocumentType.DNI.value, nullable=False)
    document_number: Mapped[str | None] = mapped_column(String(20), index=True)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name_paternal: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name_maternal: Mapped[str | None] = mapped_column(String(80))
    birth_date: Mapped[date | None] = mapped_column(Date)
    birth_place: Mapped[str | None] = mapped_column(String(120))
    sex: Mapped[str | None] = mapped_column(String(1))
    # Estado civil y ocupación se guardan ya legibles, como el grupo sanguíneo:
    # la hoja de filiación los imprime tal cual y no hay nada que traducir.
    marital_status: Mapped[str | None] = mapped_column(String(20))
    occupation: Mapped[str | None] = mapped_column(String(80))

    # Contacto
    phone: Mapped[str | None] = mapped_column(String(40))
    whatsapp: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(160))
    address: Mapped[str | None] = mapped_column(String(255))
    district: Mapped[str | None] = mapped_column(String(80))
    province: Mapped[str | None] = mapped_column(String(80))
    department: Mapped[str | None] = mapped_column(String(80))

    # Referencia de emergencia
    emergency_contact: Mapped[str | None] = mapped_column(String(160))
    emergency_phone: Mapped[str | None] = mapped_column(String(40))

    # Datos clínicos de referencia (cláusula 2.2: antecedentes y observaciones)
    blood_type: Mapped[str | None] = mapped_column(String(6))
    insurance: Mapped[str | None] = mapped_column(String(80))
    allergies: Mapped[str | None] = mapped_column(Text)
    personal_history: Mapped[str | None] = mapped_column(Text)
    family_history: Mapped[str | None] = mapped_column(Text)
    surgical_history: Mapped[str | None] = mapped_column(Text)
    current_medication: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def full_name(self) -> str:
        parts = [self.last_name_paternal, self.last_name_maternal, self.first_name]
        return " ".join(part for part in parts if part)

    @property
    def display_name(self) -> str:
        """Nombre en orden natural, para documentos y mensajes al paciente."""
        parts = [self.first_name, self.last_name_paternal, self.last_name_maternal]
        return " ".join(part for part in parts if part)

    @property
    def age(self) -> int | None:
        if self.birth_date is None:
            return None
        reference = today()
        years = reference.year - self.birth_date.year
        if (reference.month, reference.day) < (self.birth_date.month, self.birth_date.day):
            years -= 1
        return max(years, 0)

    @property
    def sex_label(self) -> str | None:
        return SEX_LABELS.get(self.sex or "")

    @property
    def document_label(self) -> str:
        name, _ = DOCUMENT_CATALOG.get(DocumentType(self.document_type), (self.document_type, None))
        return f"{name} {self.document_number}" if self.document_number else name

    @property
    def has_alerts(self) -> bool:
        """Antecedentes que el personal debe ver antes de atender."""
        return bool(self.allergies or self.current_medication)

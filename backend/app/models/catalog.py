from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Specialty(Base, TimestampMixin):
    """Especialidad o servicio asistencial que ofrece el policlínico."""

    __tablename__ = "specialties"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    default_duration_minutes: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    services: Mapped[list["MedicalService"]] = relationship(back_populates="specialty")


class ServiceKind(StrEnum):
    CONSULTA = "CONSULTA"
    PROCEDIMIENTO = "PROCEDIMIENTO"
    LABORATORIO = "LABORATORIO"
    IMAGENES = "IMAGENES"
    OTRO = "OTRO"


SERVICE_KIND_LABELS: dict[str, str] = {
    ServiceKind.CONSULTA.value: "Consulta",
    ServiceKind.PROCEDIMIENTO.value: "Procedimiento",
    ServiceKind.LABORATORIO.value: "Laboratorio",
    ServiceKind.IMAGENES.value: "Imágenes / Rayos X",
    ServiceKind.OTRO.value: "Otro",
}


class MedicalService(Base, TimestampMixin):
    """Tarifario: servicio facturable con su precio de lista."""

    __tablename__ = "medical_services"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default=ServiceKind.CONSULTA.value, nullable=False)
    specialty_id: Mapped[int | None] = mapped_column(ForeignKey("specialties.id"))
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    specialty: Mapped[Specialty | None] = relationship(back_populates="services", lazy="joined")

    @property
    def specialty_name(self) -> str | None:
        return self.specialty.name if self.specialty else None

    @property
    def kind_label(self) -> str:
        return SERVICE_KIND_LABELS.get(self.kind, self.kind)

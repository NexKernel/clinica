from enum import StrEnum

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class RoleCode(StrEnum):
    ADMIN = "ADMIN"
    RECEPCION = "RECEPCION"
    MEDICO = "MEDICO"
    ENFERMERIA = "ENFERMERIA"
    CAJA = "CAJA"
    ALMACEN = "ALMACEN"
    LABORATORIO = "LABORATORIO"
    OPTOMETRIA = "OPTOMETRIA"


# Perfil -> (nombre visible, descripción de acceso)
ROLE_CATALOG: dict[RoleCode, tuple[str, str]] = {
    RoleCode.ADMIN: ("Administrador", "Acceso total al sistema y a la configuración"),
    RoleCode.RECEPCION: ("Recepción", "Admisión de pacientes, citas y secretaría"),
    RoleCode.MEDICO: ("Médico", "Consultas, historias clínicas y órdenes"),
    RoleCode.ENFERMERIA: ("Enfermería", "Triaje, signos vitales y apoyo asistencial"),
    RoleCode.CAJA: ("Caja", "Cobros, comprobantes y arqueo de caja"),
    RoleCode.ALMACEN: ("Almacén / Farmacia", "Stock, dispensación y compras"),
    RoleCode.LABORATORIO: ("Laboratorio", "Órdenes y resultados de laboratorio"),
    RoleCode.OPTOMETRIA: ("Optometría", "Evaluaciones y medidas ópticas"),
}


# Perfiles que atienden pacientes. Su usuario lleva ficha en Profesionales y
# figura en los selectores de la agenda y de las atenciones; el resto del
# personal (administración, recepción, caja, almacén) no tiene agenda propia.
CLINICAL_ROLES: frozenset[str] = frozenset(
    {
        RoleCode.MEDICO.value,
        RoleCode.ENFERMERIA.value,
        RoleCode.LABORATORIO.value,
        RoleCode.OPTOMETRIA.value,
    }
)


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="role_ref")  # noqa: F821

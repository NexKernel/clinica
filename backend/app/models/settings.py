from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

SETTINGS_ID = 1


class ClinicSettings(Base, TimestampMixin):
    """Configuración general del establecimiento (registro único)."""

    __tablename__ = "clinic_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=SETTINGS_ID)

    # Identidad
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    short_name: Mapped[str] = mapped_column(String(40), nullable=False)
    tagline: Mapped[str | None] = mapped_column(String(200))
    legal_name: Mapped[str | None] = mapped_column(String(200))
    tax_id: Mapped[str | None] = mapped_column(String(20))
    logo_path: Mapped[str | None] = mapped_column(String(255))

    # Contacto y ubicación
    address: Mapped[str | None] = mapped_column(String(255))
    district: Mapped[str | None] = mapped_column(String(80))
    province: Mapped[str | None] = mapped_column(String(80))
    department: Mapped[str | None] = mapped_column(String(80))
    phone: Mapped[str | None] = mapped_column(String(40))
    whatsapp: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(160))
    website: Mapped[str | None] = mapped_column(String(160))

    # Datos clínicos del establecimiento
    health_facility_code: Mapped[str | None] = mapped_column(String(40))
    medical_director: Mapped[str | None] = mapped_column(String(160))
    # Categoría del establecimiento (I-1 … III-2), citada en los documentos que
    # advierten al paciente sobre la capacidad resolutiva del policlínico.
    category: Mapped[str | None] = mapped_column(String(10))
    # Pie de página de los documentos impresos (informes, consentimientos).
    document_footer: Mapped[str | None] = mapped_column(String(255))

    # Parámetros de atención (módulos de citas y consultas)
    opening_hours: Mapped[str | None] = mapped_column(String(160))
    appointment_slot_minutes: Mapped[int] = mapped_column(Integer, default=20, nullable=False)

    # Parámetros de caja y facturación
    currency: Mapped[str] = mapped_column(String(3), default="PEN", nullable=False)
    tax_rate: Mapped[float] = mapped_column(Float, default=18.0, nullable=False)
    invoice_series: Mapped[str | None] = mapped_column(String(10))
    receipt_series: Mapped[str | None] = mapped_column(String(10))

    @property
    def logo_url(self) -> str | None:
        return f"/media/{self.logo_path}" if self.logo_path else None

    @property
    def location(self) -> str | None:
        parts: list[str] = []
        for part in (self.district, self.province, self.department):
            if part and part not in parts:
                parts.append(part)
        return ", ".join(parts) or None

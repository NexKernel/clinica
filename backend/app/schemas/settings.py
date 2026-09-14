from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.types import LocalDatetime


class ClinicSettingsBase(BaseModel):
    # Identidad
    name: str = Field(min_length=3, max_length=160)
    short_name: str = Field(min_length=2, max_length=40)
    tagline: str | None = Field(default=None, max_length=200)
    legal_name: str | None = Field(default=None, max_length=200)
    tax_id: str | None = Field(default=None, max_length=20)

    # Contacto y ubicación
    address: str | None = Field(default=None, max_length=255)
    district: str | None = Field(default=None, max_length=80)
    province: str | None = Field(default=None, max_length=80)
    department: str | None = Field(default=None, max_length=80)
    phone: str | None = Field(default=None, max_length=40)
    whatsapp: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=160)
    website: str | None = Field(default=None, max_length=160)

    # Establecimiento de salud
    health_facility_code: str | None = Field(default=None, max_length=40)
    medical_director: str | None = Field(default=None, max_length=160)
    category: str | None = Field(default=None, max_length=10)

    # Documentos impresos (informes, consentimientos, actas)
    document_footer: str | None = Field(default=None, max_length=255)

    # Atención
    opening_hours: str | None = Field(default=None, max_length=160)
    appointment_slot_minutes: int = Field(default=20, ge=5, le=180)

    # Caja y facturación
    currency: str = Field(default="PEN", min_length=3, max_length=3)
    tax_rate: float = Field(default=18.0, ge=0, le=100)
    invoice_series: str | None = Field(default=None, max_length=10)
    receipt_series: str | None = Field(default=None, max_length=10)

    @field_validator("*", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = " ".join(value.split())
            return cleaned or None
        return value

    @field_validator("currency")
    @classmethod
    def _upper_currency(cls, value: str) -> str:
        return value.upper()


class ClinicSettingsUpdate(ClinicSettingsBase):
    """Payload completo de actualización (sólo perfil ADMIN)."""


class ClinicSettingsRead(ClinicSettingsBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    logo_url: str | None
    location: str | None
    updated_at: LocalDatetime


class PublicBranding(BaseModel):
    """Identidad visible antes de iniciar sesión."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    short_name: str
    tagline: str | None
    location: str | None
    address: str | None
    phone: str | None
    logo_url: str | None

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.catalog import ServiceKind


class _CleanStrings(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = " ".join(value.split())
            return cleaned or None
        return value


class SpecialtyBase(_CleanStrings):
    name: str = Field(min_length=3, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    default_duration_minutes: int = Field(default=20, ge=5, le=180)
    is_active: bool = True


class SpecialtyCreate(SpecialtyBase):
    """Alta de especialidad."""


class SpecialtyUpdate(SpecialtyBase):
    """Actualización de especialidad."""


class SpecialtyRead(SpecialtyBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class MedicalServiceBase(_CleanStrings):
    code: str = Field(min_length=2, max_length=20)
    name: str = Field(min_length=3, max_length=160)
    kind: ServiceKind = ServiceKind.CONSULTA
    specialty_id: int | None = None
    price: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=10, decimal_places=2)
    duration_minutes: int = Field(default=20, ge=5, le=180)
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def _upper_code(cls, value: str) -> str:
        return value.upper().replace(" ", "")


class MedicalServiceCreate(MedicalServiceBase):
    """Alta de servicio del tarifario."""


class MedicalServiceUpdate(MedicalServiceBase):
    """Actualización de servicio del tarifario."""


class MedicalServiceRead(MedicalServiceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    specialty_name: str | None
    kind_label: str

from datetime import time

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class ScheduleBase(BaseModel):
    weekday: int = Field(ge=0, le=6, description="0 = lunes ... 6 = domingo")
    start_time: time
    end_time: time
    is_active: bool = True

    @model_validator(mode="after")
    def _check_range(self) -> "ScheduleBase":
        if self.start_time >= self.end_time:
            raise ValueError("La hora de inicio debe ser anterior a la hora de fin")
        return self


class ScheduleWrite(ScheduleBase):
    """Bloque horario enviado al guardar la agenda del profesional."""


class ScheduleRead(ScheduleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    weekday_label: str


class PractitionerBase(BaseModel):
    full_name: str = Field(min_length=5, max_length=160)
    specialty_id: int | None = None
    user_id: int | None = None
    license_number: str | None = Field(default=None, max_length=30)
    document_number: str | None = Field(default=None, max_length=20)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = Field(default=None, max_length=160)
    slot_minutes: int = Field(default=20, ge=5, le=180)
    is_active: bool = True

    @field_validator("*", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = " ".join(value.split())
            return cleaned or None
        return value


class PractitionerCreate(PractitionerBase):
    schedules: list[ScheduleWrite] = Field(default_factory=list)


class PractitionerUpdate(PractitionerBase):
    schedules: list[ScheduleWrite] | None = Field(
        default=None, description="Si se omite, la agenda semanal no se modifica"
    )


class PractitionerRead(PractitionerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    specialty_name: str | None
    display_name: str
    schedules: list[ScheduleRead]


class PractitionerSummary(BaseModel):
    """Profesional en selectores de agenda y atenciones."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    specialty_name: str | None
    slot_minutes: int
    is_active: bool

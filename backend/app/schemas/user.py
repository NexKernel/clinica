from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.types import LocalDatetime

USERNAME_PATTERN = r"^[a-zA-Z0-9._-]+$"


def validate_password_strength(value: str) -> str:
    if not any(char.isalpha() for char in value):
        raise ValueError("La contraseña debe incluir al menos una letra")
    if not any(char.isdigit() for char in value):
        raise ValueError("La contraseña debe incluir al menos un número")
    return value


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    is_active: bool = True


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    role_name: str
    practitioner_id: int | None = None
    created_at: LocalDatetime
    updated_at: LocalDatetime


class UserListResponse(BaseModel):
    items: list[UserRead]
    total: int
    page: int
    page_size: int


class RoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: str | None
    is_active: bool


class _UserWritableFields(BaseModel):
    full_name: str = Field(min_length=3, max_length=160)
    email: EmailStr = Field(max_length=160)
    username: str = Field(min_length=3, max_length=50, pattern=USERNAME_PATTERN)

    @field_validator("full_name", mode="before")
    @classmethod
    def _clean_full_name(cls, value: object) -> object:
        return " ".join(value.split()) if isinstance(value, str) else value

    @field_validator("username", mode="before")
    @classmethod
    def _clean_username(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class ProfileUpdate(_UserWritableFields):
    """Datos que un usuario puede modificar de su propio perfil."""


class UserCreate(_UserWritableFields):
    """Alta de usuario realizada por un administrador."""

    role: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    is_active: bool = True

    @field_validator("password")
    @classmethod
    def _check_password(cls, value: str) -> str:
        return validate_password_strength(value)


class UserAdminUpdate(_UserWritableFields):
    """Actualización de un usuario realizada por un administrador."""

    role: str = Field(min_length=3, max_length=32)
    is_active: bool = True


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _check_password(cls, value: str) -> str:
        return validate_password_strength(value)


class PasswordReset(BaseModel):
    """Restablecimiento de contraseña hecho por un administrador."""

    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def _check_password(cls, value: str) -> str:
        return validate_password_strength(value)

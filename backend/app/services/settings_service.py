from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.models import SETTINGS_ID, ClinicSettings
from app.repositories.settings_repository import SettingsRepository
from app.schemas.settings import ClinicSettingsUpdate
from app.services.exceptions import BusinessRuleError

LOGO_DIR = "branding"
ALLOWED_LOGO_TYPES: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}

DEFAULT_SETTINGS = {
    "name": "Policlínico Estabridis",
    "short_name": "ESTABRIDIS",
    "tagline": "Atención médica integral para tu familia",
    "district": "Satipo",
    "province": "Satipo",
    "department": "Junín",
    "opening_hours": "Lunes a sábado, 8:00 a 20:00",
}


class SettingsService:
    """Configuración general del establecimiento y su logotipo."""

    def __init__(self, db: Session) -> None:
        self.repo = SettingsRepository(db)

    def get(self) -> ClinicSettings:
        current = self.repo.get()
        if current is None:
            current = self.repo.save(ClinicSettings(id=SETTINGS_ID, **DEFAULT_SETTINGS))
        return current

    def update(self, payload: ClinicSettingsUpdate) -> ClinicSettings:
        current = self.get()
        for field, value in payload.model_dump().items():
            setattr(current, field, value)
        return self.repo.save(current)

    def save_logo(self, content: bytes, content_type: str | None) -> ClinicSettings:
        extension = ALLOWED_LOGO_TYPES.get((content_type or "").lower())
        if extension is None:
            raise BusinessRuleError("Formato no permitido. Use PNG, JPG o WEBP")
        if not content:
            raise BusinessRuleError("El archivo está vacío")
        if len(content) > app_settings.MAX_LOGO_BYTES:
            limit_mb = app_settings.MAX_LOGO_BYTES // (1024 * 1024)
            raise BusinessRuleError(f"El logo no debe superar {limit_mb} MB")

        directory = app_settings.media_path / LOGO_DIR
        directory.mkdir(parents=True, exist_ok=True)

        filename = f"logo-{uuid4().hex}{extension}"
        (directory / filename).write_bytes(content)

        current = self.get()
        self._remove_file(current.logo_path)
        current.logo_path = f"{LOGO_DIR}/{filename}"
        return self.repo.save(current)

    def delete_logo(self) -> ClinicSettings:
        current = self.get()
        self._remove_file(current.logo_path)
        current.logo_path = None
        return self.repo.save(current)

    @staticmethod
    def _remove_file(relative_path: str | None) -> None:
        if not relative_path:
            return
        target = Path(app_settings.media_path / relative_path)
        target.unlink(missing_ok=True)

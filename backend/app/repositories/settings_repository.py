from sqlalchemy.orm import Session

from app.models import SETTINGS_ID, ClinicSettings


class SettingsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self) -> ClinicSettings | None:
        return self.db.get(ClinicSettings, SETTINGS_ID)

    def save(self, settings: ClinicSettings) -> ClinicSettings:
        self.db.add(settings)
        self.db.commit()
        self.db.refresh(settings)
        return settings

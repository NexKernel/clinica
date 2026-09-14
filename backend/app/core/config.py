from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    PROJECT_NAME: str = "Policlínico Estabridis"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    TIMEZONE: str = "America/Lima"

    POSTGRES_USER: str = "estabridis"
    POSTGRES_PASSWORD: str = "estabridis"
    POSTGRES_DB: str = "estabridis"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str | None = None

    SECRET_KEY: str = "cambiar-esta-clave-en-produccion"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    BACKEND_CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    MEDIA_DIR: str = "media"
    MAX_LOGO_BYTES: int = 2 * 1024 * 1024

    # Archivos clínicos: se guardan fuera de /media y se sirven con autorización.
    STORAGE_DIR: str = "storage"
    MAX_ATTACHMENT_BYTES: int = 10 * 1024 * 1024

    # Enlaces de resultados enviados al paciente (WhatsApp)
    PUBLIC_APP_URL: str = "http://localhost:5173"
    SHARE_LINK_HOURS: int = 72
    DEFAULT_PHONE_COUNTRY_CODE: str = "51"

    FIRST_ADMIN_USERNAME: str = "admin"
    FIRST_ADMIN_EMAIL: str = "admin@estabridis.pe"
    FIRST_ADMIN_PASSWORD: str = "Admin123*"
    FIRST_ADMIN_FULL_NAME: str = "Administrador del Sistema"

    @property
    def media_path(self) -> Path:
        return self._resolve(self.MEDIA_DIR)

    @property
    def storage_path(self) -> Path:
        """Raíz de los archivos clínicos, no expuesta como contenido estático."""
        return self._resolve(self.STORAGE_DIR)

    @staticmethod
    def _resolve(directory: str) -> Path:
        path = Path(directory)
        return path if path.is_absolute() else Path.cwd() / path

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.BACKEND_CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def sqlalchemy_uri(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

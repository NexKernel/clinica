"""Horario oficial del sistema: America/Lima (UTC-5, sin horario de verano)."""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.core.config import settings

LIMA = ZoneInfo(settings.TIMEZONE)

# Abreviaturas usadas en los gráficos del panel de indicadores.
LOCALE_WEEKDAYS: tuple[str, ...] = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")


def now() -> datetime:
    """Instante actual expresado en la zona horaria del policlínico."""
    return datetime.now(LIMA)


def today() -> date:
    """Fecha de hoy según el horario de Perú (no la del servidor)."""
    return now().date()


def to_local(value: datetime) -> datetime:
    """Convierte cualquier instante a la zona del policlínico.

    Un datetime sin zona se asume ya expresado en horario de Perú.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=LIMA)
    return value.astimezone(LIMA)


def start_of_day(value: date | None = None) -> datetime:
    """Inicio del día local; útil para filtros de agenda, caja y reportes."""
    return datetime.combine(value or today(), time.min, tzinfo=LIMA)


def end_of_day(value: date | None = None) -> datetime:
    return datetime.combine(value or today(), time.max, tzinfo=LIMA)


def as_date(value: date | datetime | str) -> date:
    """Normaliza el resultado de func.date, que varía según el motor de BD."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        return date.fromisoformat(value)
    return value

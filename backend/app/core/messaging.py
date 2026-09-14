"""Utilidades de contacto con el paciente (WhatsApp).

El contrato excluye la contratación de WhatsApp Business/API: el sistema deja
listo el mensaje y el enlace, y el personal lo envía desde su propia cuenta.
"""

from urllib.parse import quote

from app.core.config import settings

WHATSAPP_BASE_URL = "https://wa.me"


def international_phone(phone: str | None) -> str | None:
    """Normaliza un número peruano de 9 dígitos a formato internacional."""
    if not phone:
        return None
    digits = "".join(char for char in phone if char.isdigit())
    if not digits:
        return None
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 9:
        return f"{settings.DEFAULT_PHONE_COUNTRY_CODE}{digits}"
    return digits


def whatsapp_url(phone: str | None, message: str) -> str | None:
    """Enlace wa.me con el mensaje precargado; None si no hay número válido."""
    normalized = international_phone(phone)
    if normalized is None:
        return None
    return f"{WHATSAPP_BASE_URL}/{normalized}?text={quote(message)}"

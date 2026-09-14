from typing import Literal

from pydantic import BaseModel

Severity = Literal["info", "warning", "danger"]


class Notification(BaseModel):
    """Aviso operativo que la campanita muestra al usuario."""

    code: str
    module: str
    title: str
    description: str
    count: int
    severity: Severity


class NotificationFeed(BaseModel):
    """Avisos vigentes para el perfil que consulta.

    `total` es la suma de los pendientes, no la cantidad de avisos: es la cifra
    que se pinta sobre la campanita.
    """

    total: int
    items: list[Notification]

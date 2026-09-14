"""Registro de acciones relevantes del sistema (cláusula 2.10).

El middleware anota cada operación que modifica información: quién la hizo,
sobre qué módulo, con qué resultado y desde qué dirección. Las consultas de
sólo lectura no se registran, para que la bitácora siga siendo legible.
"""

import logging
from dataclasses import dataclass

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.db.session import SessionLocal
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class AuditActor:
    """Datos del autor copiados al autenticar.

    El middleware se ejecuta cuando la sesión de la petición ya se cerró, de
    modo que no puede leer atributos del objeto ORM sin provocar una carga
    diferida sobre una sesión muerta.
    """

    id: int
    username: str
    role: str


AUDITED_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Rutas que no aportan a la bitácora o que no deben quedar registradas.
IGNORED_PREFIXES: tuple[str, ...] = ("/api/v1/auth/logout",)

# Primer segmento de la ruta -> módulo mostrado en la bitácora.
MODULE_BY_SEGMENT: dict[str, str] = {
    "auth": "Acceso",
    "users": "Usuarios",
    "roles": "Perfiles",
    "settings": "Configuración",
    "patients": "Pacientes",
    "appointments": "Agenda de citas",
    "practitioners": "Profesionales",
    "catalog": "Catálogos",
    "encounters": "Atenciones",
    "studies": "Resultados y Rayos X",
    "reminders": "Recordatorios",
    "inventory": "Farmacia y almacén",
    "purchases": "Compras",
    "sales": "Ventas y facturación",
}


class AuditMiddleware(BaseHTTPMiddleware):
    """Anota en la bitácora las operaciones que modifican información."""

    def __init__(self, app, api_prefix: str) -> None:
        super().__init__(app)
        self.api_prefix = api_prefix.rstrip("/")

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        if self._should_record(request):
            self._record(request, response.status_code)
        return response

    def _should_record(self, request: Request) -> bool:
        path = request.url.path
        if request.method not in AUDITED_METHODS:
            return False
        if not path.startswith(self.api_prefix):
            return False
        return not path.startswith(IGNORED_PREFIXES)

    def _record(self, request: Request, status_code: int) -> None:
        actor: AuditActor | None = getattr(request.state, "audit_actor", None)
        path = request.url.path
        try:
            with SessionLocal() as db:
                db.add(
                    AuditLog(
                        user_id=actor.id if actor else None,
                        username=actor.username if actor else None,
                        role=actor.role if actor else None,
                        action=request.method,
                        module=module_for(path, self.api_prefix),
                        path=path[:255],
                        entity_id=_entity_id(path),
                        status_code=status_code,
                        ip_address=_client_ip(request),
                    )
                )
                db.commit()
        except Exception:  # pragma: no cover - la bitácora no debe romper la operación
            logger.exception("No fue posible registrar la acción en la bitácora")


def module_for(path: str, api_prefix: str) -> str:
    segments = [part for part in path[len(api_prefix) :].split("/") if part]
    if not segments:
        return "Sistema"
    return MODULE_BY_SEGMENT.get(segments[0], segments[0].capitalize())


def _entity_id(path: str) -> str | None:
    """Último identificador numérico de la ruta, si lo hay."""
    for segment in reversed(path.split("/")):
        if segment.isdigit():
            return segment
    return None


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:45]
    return request.client.host if request.client else None

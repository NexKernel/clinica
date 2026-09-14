from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.schemas.notification import NotificationFeed
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationFeed)
def list_notifications(db: DbSession, current_user: CurrentUser) -> NotificationFeed:
    """Avisos operativos del perfil en sesión, para la campanita de la barra.

    Cualquier usuario autenticado puede consultarlos: el recorte lo hace el
    servicio, que solo cuenta los módulos que su perfil tiene permitido ver.
    """
    return NotificationService(db).feed(current_user.role)

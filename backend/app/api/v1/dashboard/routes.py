from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.core.permissions import ModuleCode, can_view
from app.schemas.dashboard import DashboardSummary
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    db: DbSession,
    current_user: CurrentUser,
    day: Annotated[date | None, Query(description="Fecha del resumen; por defecto hoy")] = None,
) -> DashboardSummary:
    """Indicadores del día: agenda, atenciones, caja y alertas de almacén.

    Las cifras de caja solo viajan a los perfiles con acceso de consulta al
    módulo de ventas; para el resto el panel llega sin ellas.
    """
    return DashboardService(db).summary(
        day, include_revenue=can_view(current_user.role, ModuleCode.SALES)
    )

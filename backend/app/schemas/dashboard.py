from datetime import date

from pydantic import BaseModel

from app.schemas.appointment import AppointmentRead
from app.schemas.inventory import LowStockItem


class DashboardTotals(BaseModel):
    """Cifras del día en curso, con su variación respecto de ayer.

    Las cifras de caja llegan en `None` a los perfiles que no tienen acceso de
    consulta al módulo de ventas: el panel no puede ser una vía indirecta para
    ver lo que la matriz de permisos les niega.
    """

    appointments_today: int
    appointments_yesterday: int
    attended_today: int
    pending_today: int
    revenue_today: float | None
    revenue_yesterday: float | None
    patients_total: int
    patients_new_today: int


class SeriesPoint(BaseModel):
    day: date
    label: str
    value: float


class StatusSlice(BaseModel):
    status: str
    label: str
    value: int


class OperationAlerts(BaseModel):
    low_stock: int
    expiring_soon: int
    expired: int
    pending_studies: int
    pending_reminders: int
    draft_purchases: int


class DashboardSummary(BaseModel):
    """Resumen operativo que abre el sistema (cláusula 3)."""

    day: date
    totals: DashboardTotals
    attentions_series: list[SeriesPoint]
    revenue_series: list[SeriesPoint]
    appointment_status: list[StatusSlice]
    alerts: OperationAlerts
    upcoming_appointments: list[AppointmentRead]
    restock_items: list[LowStockItem]

"""Avisos operativos que alimentan la campanita de la barra superior.

No hay una tabla de notificaciones: cada aviso es una consulta al estado real
del sistema (agenda del día, recordatorios vencidos, resultados sin cargar,
existencias, compras sin cerrar). Así nunca queda desincronizado con los datos
ni hay que mantener una bandeja aparte.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.core.datetime import now, today
from app.core.permissions import ModuleCode, can_view
from app.models.appointment import AppointmentStatus
from app.models.purchase import PurchaseStatus
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.inventory_repository import ProductRepository
from app.repositories.purchase_repository import PurchaseRepository
from app.repositories.reminder_repository import ReminderRepository
from app.repositories.study_repository import StudyRepository
from app.schemas.notification import Notification, NotificationFeed, Severity


@dataclass(frozen=True)
class _Source:
    """Origen de un aviso: cómo se cuenta y cómo se redacta."""

    code: str
    module: ModuleCode
    severity: Severity
    title: str
    singular: str
    plural: str


# El orden es el de la campanita: primero lo que frena una atención, después lo
# que compromete el stock y al final lo administrativo.
SOURCES: tuple[_Source, ...] = (
    _Source(
        code="pending_appointments",
        module=ModuleCode.APPOINTMENTS,
        severity="info",
        title="Citas por atender",
        singular="cita programada para hoy sigue pendiente",
        plural="citas programadas para hoy siguen pendientes",
    ),
    _Source(
        code="overdue_reminders",
        module=ModuleCode.REMINDERS,
        severity="warning",
        title="Recordatorios vencidos",
        singular="recordatorio pasó su hora de envío",
        plural="recordatorios pasaron su hora de envío",
    ),
    _Source(
        code="pending_studies",
        module=ModuleCode.STUDIES,
        severity="warning",
        title="Resultados pendientes",
        singular="estudio espera la carga de su resultado",
        plural="estudios esperan la carga de su resultado",
    ),
    _Source(
        code="expired_products",
        module=ModuleCode.PHARMACY,
        severity="danger",
        title="Productos vencidos",
        singular="producto pasó su fecha de vencimiento",
        plural="productos pasaron su fecha de vencimiento",
    ),
    _Source(
        code="low_stock",
        module=ModuleCode.PHARMACY,
        severity="warning",
        title="Stock bajo mínimo",
        singular="producto está por debajo de su stock mínimo",
        plural="productos están por debajo de su stock mínimo",
    ),
    _Source(
        code="expiring_products",
        module=ModuleCode.PHARMACY,
        severity="warning",
        title="Próximos a vencer",
        singular="producto vence dentro de poco",
        plural="productos vencen dentro de poco",
    ),
    _Source(
        code="draft_purchases",
        module=ModuleCode.PURCHASES,
        severity="info",
        title="Compras en borrador",
        singular="compra quedó sin confirmar",
        plural="compras quedaron sin confirmar",
    ),
)


class NotificationService:
    """Avisos vigentes, recortados a lo que el perfil puede consultar."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.appointments = AppointmentRepository(db)
        self.reminders = ReminderRepository(db)
        self.studies = StudyRepository(db)
        self.products = ProductRepository(db)
        self.purchases = PurchaseRepository(db)

    def feed(self, role_code: str, day: date | None = None) -> NotificationFeed:
        reference = day or today()
        # Solo se consulta el origen que el perfil puede ver: la campanita no
        # puede filtrar información que la matriz de permisos le niega.
        visible = [source for source in SOURCES if can_view(role_code, source.module)]
        counts = self._counts(visible, reference)

        items = [
            Notification(
                code=source.code,
                module=source.module.value,
                title=source.title,
                description=self._describe(source, counts[source.code]),
                count=counts[source.code],
                severity=source.severity,
            )
            for source in visible
            if counts[source.code] > 0
        ]
        return NotificationFeed(total=sum(item.count for item in items), items=items)

    def _counts(self, sources: list[_Source], reference: date) -> dict[str, int]:
        counters = {source.code: 0 for source in sources}
        for code in counters:
            counters[code] = self._count(code, reference)
        return counters

    def _count(self, code: str, reference: date) -> int:
        if code == "pending_appointments":
            by_status = self.appointments.count_by_status(reference)
            return by_status.get(AppointmentStatus.PROGRAMADA.value, 0) + by_status.get(
                AppointmentStatus.CONFIRMADA.value, 0
            )
        if code == "overdue_reminders":
            return self.reminders.count_overdue(now())
        if code == "pending_studies":
            return self.studies.count_pending()
        if code == "expired_products":
            return self.products.count_expired()
        if code == "low_stock":
            return self.products.count_low_stock()
        if code == "expiring_products":
            return self.products.count_expiring()
        if code == "draft_purchases":
            return self.purchases.count_by_status(PurchaseStatus.BORRADOR.value)
        return 0

    @staticmethod
    def _describe(source: _Source, count: int) -> str:
        return f"{count} {source.singular if count == 1 else source.plural}"

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.datetime import LOCALE_WEEKDAYS, now, today
from app.models.appointment import APPOINTMENT_STATUS_LABELS, Appointment, AppointmentStatus
from app.models.purchase import PurchaseStatus
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.encounter_repository import EncounterRepository
from app.repositories.inventory_repository import ProductRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.purchase_repository import PurchaseRepository
from app.repositories.reminder_repository import ReminderRepository
from app.repositories.sale_repository import SaleRepository
from app.repositories.study_repository import StudyRepository
from app.schemas.dashboard import (
    DashboardSummary,
    DashboardTotals,
    OperationAlerts,
    SeriesPoint,
    StatusSlice,
)

SERIES_DAYS = 7
UPCOMING_LIMIT = 6
RESTOCK_LIMIT = 5


class DashboardService:
    """Indicadores operativos del policlínico, calculados sobre datos reales."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.appointments = AppointmentRepository(db)
        self.encounters = EncounterRepository(db)
        self.sales = SaleRepository(db)
        self.patients = PatientRepository(db)
        self.products = ProductRepository(db)
        self.studies = StudyRepository(db)
        self.reminders = ReminderRepository(db)
        self.purchases = PurchaseRepository(db)

    def summary(
        self, day: date | None = None, *, include_revenue: bool = True
    ) -> DashboardSummary:
        """Resumen del día.

        Con `include_revenue=False` el panel se arma sin las cifras de caja,
        para los perfiles que no pueden consultar el módulo de ventas.
        """
        reference = day or today()
        previous = reference - timedelta(days=1)
        since = reference - timedelta(days=SERIES_DAYS - 1)

        counters = self.appointments.count_by_status(reference)
        pending = counters.get(AppointmentStatus.PROGRAMADA.value, 0) + counters.get(
            AppointmentStatus.CONFIRMADA.value, 0
        )

        return DashboardSummary(
            day=reference,
            totals=DashboardTotals(
                appointments_today=sum(counters.values()),
                appointments_yesterday=self.appointments.count_in_range(
                    date_from=previous, date_to=previous
                ),
                attended_today=counters.get(AppointmentStatus.ATENDIDA.value, 0),
                pending_today=pending,
                revenue_today=round(self.sales.revenue_in_range(reference, reference), 2)
                if include_revenue
                else None,
                revenue_yesterday=round(self.sales.revenue_in_range(previous, previous), 2)
                if include_revenue
                else None,
                patients_total=self.patients.count_all(is_active=True),
                patients_new_today=self.patients.count_registered_since(reference),
            ),
            attentions_series=self._attentions_series(since, reference),
            revenue_series=self._revenue_series(since, reference) if include_revenue else [],
            appointment_status=[
                StatusSlice(
                    status=status,
                    label=APPOINTMENT_STATUS_LABELS.get(status, status),
                    value=value,
                )
                for status, value in sorted(counters.items())
                if value
            ],
            alerts=OperationAlerts(
                low_stock=self.products.count_low_stock(),
                expiring_soon=self.products.count_expiring(),
                expired=self.products.count_expired(),
                pending_studies=self.studies.count_pending(),
                pending_reminders=self.reminders.count_overdue(now()),
                draft_purchases=self.purchases.count_by_status(PurchaseStatus.BORRADOR.value),
            ),
            upcoming_appointments=self._upcoming(reference),
            restock_items=self.products.list_low_stock(RESTOCK_LIMIT),
        )

    # --- Series ---------------------------------------------------------
    def _attentions_series(self, since: date, until: date) -> list[SeriesPoint]:
        counts = dict(self.encounters.daily_counts(since, until))
        return [
            SeriesPoint(day=day, label=_weekday_label(day), value=float(counts.get(day, 0)))
            for day in _days_between(since, until)
        ]

    def _revenue_series(self, since: date, until: date) -> list[SeriesPoint]:
        revenue = dict(self.sales.daily_revenue(since, until))
        return [
            SeriesPoint(day=day, label=_weekday_label(day), value=round(revenue.get(day, 0.0), 2))
            for day in _days_between(since, until)
        ]

    def _upcoming(self, reference: date) -> list[Appointment]:
        """Próximas citas del día, en orden de atención."""
        pending_statuses = (
            AppointmentStatus.PROGRAMADA.value,
            AppointmentStatus.CONFIRMADA.value,
            AppointmentStatus.EN_ATENCION.value,
        )
        agenda = [
            appointment
            for appointment in self.appointments.list_for_day(reference)
            if appointment.status in pending_statuses
        ]
        return agenda[:UPCOMING_LIMIT]


def _days_between(since: date, until: date) -> list[date]:
    span = (until - since).days
    return [since + timedelta(days=offset) for offset in range(span + 1)]


def _weekday_label(day: date) -> str:
    return LOCALE_WEEKDAYS[day.weekday()]

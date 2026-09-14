from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.core.datetime import LIMA, now, start_of_day, to_local
from app.models.appointment import BLOCKING_STATUSES, Appointment, AppointmentStatus
from app.models.patient import Patient
from app.models.practitioner import Practitioner
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.catalog_repository import MedicalServiceRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.practitioner_repository import PractitionerRepository
from app.schemas.appointment import (
    AgendaSummary,
    AppointmentCreate,
    AppointmentSlot,
    AppointmentUpdate,
    DayAvailability,
)
from app.schemas.common import Pagination
from app.services.exceptions import BusinessRuleError, ConflictError, NotFoundError

# Días que puede abarcar la agenda en una sola consulta. La vista de calendario
# necesita el mes completo; más allá de eso conviene paginar con /appointments.
MAX_AGENDA_DAYS = 42

# Transiciones permitidas entre estados de una cita.
ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    AppointmentStatus.PROGRAMADA.value: (
        AppointmentStatus.CONFIRMADA.value,
        AppointmentStatus.EN_ATENCION.value,
        AppointmentStatus.ATENDIDA.value,
        AppointmentStatus.CANCELADA.value,
        AppointmentStatus.NO_ASISTIO.value,
    ),
    AppointmentStatus.CONFIRMADA.value: (
        AppointmentStatus.EN_ATENCION.value,
        AppointmentStatus.ATENDIDA.value,
        AppointmentStatus.CANCELADA.value,
        AppointmentStatus.NO_ASISTIO.value,
    ),
    AppointmentStatus.EN_ATENCION.value: (
        AppointmentStatus.ATENDIDA.value,
        AppointmentStatus.CANCELADA.value,
    ),
    AppointmentStatus.ATENDIDA.value: (),
    AppointmentStatus.CANCELADA.value: (AppointmentStatus.PROGRAMADA.value,),
    AppointmentStatus.NO_ASISTIO.value: (AppointmentStatus.PROGRAMADA.value,),
}


class AppointmentService:
    """Agenda de citas: programación, disponibilidad y estados (cláusula 2.1)."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.appointments = AppointmentRepository(db)
        self.patients = PatientRepository(db)
        self.practitioners = PractitionerRepository(db)
        self.services = MedicalServiceRepository(db)

    # --- Consultas ------------------------------------------------------
    def list_appointments(
        self,
        *,
        term: str | None = None,
        practitioner_id: int | None = None,
        patient_id: int | None = None,
        status: str | None = None,
        day: date | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        pagination: Pagination,
    ) -> tuple[list[Appointment], int]:
        return self.appointments.search(
            term=term,
            practitioner_id=practitioner_id,
            patient_id=patient_id,
            status=status,
            day=day,
            date_from=date_from,
            date_to=date_to,
            pagination=pagination,
        )

    def agenda_for_day(self, day: date, practitioner_id: int | None = None) -> list[Appointment]:
        return self.appointments.list_for_day(day, practitioner_id)

    def agenda_for_range(
        self, date_from: date, date_to: date, practitioner_id: int | None = None
    ) -> list[Appointment]:
        """Agenda de varios días para la vista de calendario.

        El rango se acota: la respuesta no está paginada y un intervalo abierto
        podría traer la agenda entera del establecimiento.
        """
        if date_to < date_from:
            date_from, date_to = date_to, date_from
        if (date_to - date_from).days + 1 > MAX_AGENDA_DAYS:
            raise BusinessRuleError(
                f"El rango de la agenda no puede superar {MAX_AGENDA_DAYS} días"
            )
        return self.appointments.list_in_range(date_from, date_to, practitioner_id)

    def history_for_patient(self, patient_id: int) -> list[Appointment]:
        return self.appointments.list_for_patient(patient_id)

    def get(self, appointment_id: int) -> Appointment:
        appointment = self.appointments.get_by_id(appointment_id)
        if appointment is None:
            raise NotFoundError("La cita no existe")
        return appointment

    def summary_for_day(self, day: date, practitioner_id: int | None = None) -> AgendaSummary:
        counters = self.appointments.count_by_status(day, practitioner_id)
        scheduled = counters.get(AppointmentStatus.PROGRAMADA.value, 0) + counters.get(
            AppointmentStatus.CONFIRMADA.value, 0
        )
        return AgendaSummary(
            day=day,
            total=sum(counters.values()),
            scheduled=scheduled,
            attended=counters.get(AppointmentStatus.ATENDIDA.value, 0),
            cancelled=counters.get(AppointmentStatus.CANCELADA.value, 0),
            no_show=counters.get(AppointmentStatus.NO_ASISTIO.value, 0),
        )

    def availability(self, practitioner_id: int, day: date) -> DayAvailability:
        """Espacios libres y ocupados del profesional en la fecha indicada."""
        practitioner = self._get_practitioner(practitioner_id)
        blocks = [
            schedule
            for schedule in practitioner.schedules
            if schedule.is_active and schedule.weekday == day.weekday()
        ]
        booked = [
            appointment
            for appointment in self.appointments.list_for_day(day, practitioner_id)
            if appointment.status in BLOCKING_STATUSES
        ]

        slots: list[AppointmentSlot] = []
        step = timedelta(minutes=practitioner.slot_minutes)
        for block in blocks:
            cursor = _combine(day, block.start_time)
            limit = _combine(day, block.end_time)
            while cursor + step <= limit:
                slots.append(self._build_slot(cursor, cursor + step, booked))
                cursor += step

        return DayAvailability(
            practitioner_id=practitioner.id,
            practitioner_name=practitioner.full_name,
            day=day,
            slot_minutes=practitioner.slot_minutes,
            working=bool(blocks),
            slots=slots,
        )

    # --- Programación ---------------------------------------------------
    def create(self, payload: AppointmentCreate, actor: User) -> Appointment:
        patient = self._get_patient(payload.patient_id)
        practitioner = self._get_practitioner(payload.practitioner_id)
        duration = self._resolve_duration(payload.duration_minutes, payload.service_id, practitioner)
        scheduled_at = self._validate_schedule(payload.scheduled_at, allow_past=False)
        self._ensure_free(practitioner.id, scheduled_at, duration)

        appointment = Appointment(
            patient_id=patient.id,
            practitioner_id=practitioner.id,
            service_id=payload.service_id,
            scheduled_at=scheduled_at,
            duration_minutes=duration,
            reason=payload.reason,
            notes=payload.notes,
            status=AppointmentStatus.PROGRAMADA.value,
            created_by_id=actor.id,
        )
        return self.appointments.add(appointment)

    def update(self, appointment_id: int, payload: AppointmentUpdate) -> Appointment:
        appointment = self.get(appointment_id)
        if appointment.status == AppointmentStatus.ATENDIDA.value:
            raise BusinessRuleError("No se puede modificar una cita ya atendida")

        patient = self._get_patient(payload.patient_id)
        practitioner = self._get_practitioner(payload.practitioner_id)
        duration = self._resolve_duration(payload.duration_minutes, payload.service_id, practitioner)
        scheduled_at = self._validate_schedule(
            payload.scheduled_at, allow_past=to_local(appointment.scheduled_at) < now()
        )
        self._ensure_free(practitioner.id, scheduled_at, duration, exclude_id=appointment.id)

        appointment.patient_id = patient.id
        appointment.practitioner_id = practitioner.id
        appointment.service_id = payload.service_id
        appointment.scheduled_at = scheduled_at
        appointment.duration_minutes = duration
        appointment.reason = payload.reason
        appointment.notes = payload.notes
        return self.appointments.save(appointment)

    def change_status(
        self, appointment_id: int, status: AppointmentStatus, cancel_reason: str | None = None
    ) -> Appointment:
        appointment = self.get(appointment_id)
        target = status.value

        if target == appointment.status:
            return appointment
        if target not in ALLOWED_TRANSITIONS.get(appointment.status, ()):
            raise BusinessRuleError(
                f"No es posible pasar del estado {appointment.status_label} al solicitado"
            )
        if target == AppointmentStatus.CANCELADA.value and not cancel_reason:
            raise BusinessRuleError("Indique el motivo de la cancelación")

        appointment.status = target
        appointment.cancel_reason = (
            cancel_reason if target == AppointmentStatus.CANCELADA.value else None
        )
        return self.appointments.save(appointment)

    # --- Apoyo ----------------------------------------------------------
    def _build_slot(
        self, start: datetime, end: datetime, booked: list[Appointment]
    ) -> AppointmentSlot:
        for appointment in booked:
            occupied_start = to_local(appointment.scheduled_at)
            occupied_end = occupied_start + timedelta(minutes=appointment.duration_minutes)
            if occupied_start < end and occupied_end > start:
                return AppointmentSlot(
                    start=start,
                    end=end,
                    available=False,
                    appointment_id=appointment.id,
                    patient_name=appointment.patient_name,
                    status=appointment.status,
                )
        return AppointmentSlot(start=start, end=end, available=True)

    def _ensure_free(
        self, practitioner_id: int, start: datetime, duration: int, exclude_id: int | None = None
    ) -> None:
        end = start + timedelta(minutes=duration)
        conflict = self.appointments.find_overlap(
            practitioner_id=practitioner_id, start=start, end=end, exclude_id=exclude_id
        )
        if conflict is not None:
            occupied = to_local(conflict.scheduled_at).strftime("%H:%M")
            raise ConflictError(f"El profesional ya tiene una cita a las {occupied}")

    def _resolve_duration(
        self, requested: int | None, service_id: int | None, practitioner: Practitioner
    ) -> int:
        if requested:
            return requested
        if service_id is not None:
            service = self.services.get_by_id(service_id)
            if service is None:
                raise BusinessRuleError("El servicio indicado no existe")
            return service.duration_minutes
        return practitioner.slot_minutes

    @staticmethod
    def _validate_schedule(value: datetime, *, allow_past: bool) -> datetime:
        scheduled_at = to_local(value)
        if not allow_past and scheduled_at < start_of_day():
            raise BusinessRuleError("No se pueden programar citas en fechas anteriores a hoy")
        return scheduled_at

    def _get_patient(self, patient_id: int) -> Patient:
        patient = self.patients.get_by_id(patient_id)
        if patient is None:
            raise BusinessRuleError("El paciente indicado no existe")
        if not patient.is_active:
            raise BusinessRuleError("El paciente se encuentra inactivo")
        return patient

    def _get_practitioner(self, practitioner_id: int) -> Practitioner:
        practitioner = self.practitioners.get_by_id(practitioner_id)
        if practitioner is None:
            raise BusinessRuleError("El profesional indicado no existe")
        if not practitioner.is_active:
            raise BusinessRuleError("El profesional se encuentra inactivo")
        return practitioner


def _combine(day: date, moment: time) -> datetime:
    return datetime.combine(day, moment, tzinfo=LIMA)

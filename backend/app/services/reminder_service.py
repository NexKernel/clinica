from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.datetime import end_of_day, now, start_of_day, to_local
from app.core.messaging import international_phone, whatsapp_url
from app.models.encounter import Encounter, Prescription
from app.models.reminder import Reminder, ReminderChannel, ReminderKind, ReminderStatus
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.encounter_repository import EncounterRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.reminder_repository import ReminderRepository
from app.schemas.common import Pagination
from app.schemas.reminder import (
    AppointmentReminderPlan,
    ReminderCreate,
    ReminderPlan,
    ReminderStats,
    ReminderUpdate,
    WhatsAppMessage,
)
from app.services.exceptions import BusinessRuleError, NotFoundError
from app.services.settings_service import SettingsService

# Tope de avisos generados por receta: evita agendas inmanejables en
# tratamientos prolongados. Al superarlo se programa un aviso diario.
MAX_REMINDERS_PER_PRESCRIPTION = 90


class ReminderService:
    """Recordatorios de medicación y de citas (cláusula 2.5)."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.reminders = ReminderRepository(db)
        self.patients = PatientRepository(db)
        self.appointments = AppointmentRepository(db)
        self.encounters = EncounterRepository(db)

    # --- Consultas ------------------------------------------------------
    def list_reminders(self, **filters) -> tuple[list[Reminder], int]:
        pagination: Pagination = filters.pop("pagination")
        return self.reminders.search(pagination=pagination, **filters)

    def get(self, reminder_id: int) -> Reminder:
        reminder = self.reminders.get_by_id(reminder_id)
        if reminder is None:
            raise NotFoundError("El recordatorio no existe")
        return reminder

    def pending(self) -> list[Reminder]:
        """Avisos por realizar: vencidos y los programados para hoy."""
        return self.reminders.list_pending_until(end_of_day())

    def stats(self) -> ReminderStats:
        moment = now()
        return ReminderStats(
            pending_today=self.reminders.count_pending_between(start_of_day(), end_of_day()),
            overdue=self.reminders.count_overdue(start_of_day()),
            sent_today=self.reminders.count_sent_on(moment.date()),
            upcoming_week=self.reminders.count_pending_between(
                moment, end_of_day(moment.date() + timedelta(days=7))
            ),
        )

    # --- Registro -------------------------------------------------------
    def create(self, payload: ReminderCreate, actor: User) -> Reminder:
        self._get_patient(payload.patient_id)
        reminder = Reminder(
            patient_id=payload.patient_id,
            appointment_id=payload.appointment_id,
            encounter_id=payload.encounter_id,
            prescription_id=payload.prescription_id,
            kind=payload.kind.value,
            channel=payload.channel.value,
            status=ReminderStatus.PENDIENTE.value,
            title=payload.title,
            message=payload.message,
            scheduled_for=to_local(payload.scheduled_for),
            notes=payload.notes,
            created_by_id=actor.id,
        )
        return self.reminders.add(reminder)

    def update(self, reminder_id: int, payload: ReminderUpdate) -> Reminder:
        reminder = self.get(reminder_id)
        if not reminder.is_pending:
            raise BusinessRuleError("Solo se pueden modificar recordatorios pendientes")

        reminder.patient_id = payload.patient_id
        reminder.kind = payload.kind.value
        reminder.channel = payload.channel.value
        reminder.title = payload.title
        reminder.message = payload.message
        reminder.scheduled_for = to_local(payload.scheduled_for)
        reminder.notes = payload.notes
        return self.reminders.save(reminder)

    def mark_sent(self, reminder_id: int) -> Reminder:
        reminder = self.get(reminder_id)
        if reminder.status == ReminderStatus.CANCELADO.value:
            raise BusinessRuleError("El recordatorio está cancelado")
        reminder.status = ReminderStatus.ENVIADO.value
        reminder.sent_at = now()
        return self.reminders.save(reminder)

    def cancel(self, reminder_id: int) -> Reminder:
        reminder = self.get(reminder_id)
        if reminder.status == ReminderStatus.ENVIADO.value:
            raise BusinessRuleError("El recordatorio ya fue enviado")
        reminder.status = ReminderStatus.CANCELADO.value
        return self.reminders.save(reminder)

    # --- Generación automática ------------------------------------------
    def plan_for_appointment(
        self, appointment_id: int, plan: AppointmentReminderPlan, actor: User
    ) -> list[Reminder]:
        appointment = self.appointments.get_by_id(appointment_id)
        if appointment is None:
            raise BusinessRuleError("La cita indicada no existe")
        if appointment.is_closed:
            raise BusinessRuleError("La cita ya está cerrada")

        clinic = SettingsService(self.db).get()
        scheduled_at = to_local(appointment.scheduled_at)
        remind_at = scheduled_at - timedelta(hours=plan.hours_before)
        message = (
            f"Hola {appointment.patient.display_name}, le recordamos su cita en {clinic.name} "
            f"el {scheduled_at.strftime('%d/%m/%Y')} a las {scheduled_at.strftime('%H:%M')} "
            f"con {appointment.practitioner_name}."
        )

        reminder = Reminder(
            patient_id=appointment.patient_id,
            appointment_id=appointment.id,
            kind=ReminderKind.CITA.value,
            channel=plan.channel.value,
            status=ReminderStatus.PENDIENTE.value,
            title=f"Cita {scheduled_at.strftime('%d/%m %H:%M')}",
            message=message,
            scheduled_for=remind_at,
            created_by_id=actor.id,
        )
        return self.reminders.add_many([reminder])

    def plan_for_encounter(
        self, encounter_id: int, plan: ReminderPlan, actor: User
    ) -> list[Reminder]:
        """Programa los avisos de toma de todas las recetas de la atención."""
        encounter = self.encounters.get_by_id(encounter_id)
        if encounter is None:
            raise BusinessRuleError("La atención indicada no existe")
        if not encounter.prescriptions:
            raise BusinessRuleError("La atención no tiene medicamentos indicados")

        start = to_local(plan.start_at) if plan.start_at else now()
        created: list[Reminder] = []
        for prescription in encounter.prescriptions:
            self.reminders.delete_pending_for_prescription(prescription.id)
            created.extend(
                self._build_prescription_reminders(encounter, prescription, start, plan, actor)
            )
        if not created:
            raise BusinessRuleError(
                "Las recetas no indican frecuencia ni duración: complete esos datos"
            )
        return self.reminders.add_many(created)

    def whatsapp_message(self, reminder_id: int) -> WhatsAppMessage:
        reminder = self.get(reminder_id)
        phone = international_phone(reminder.patient_phone)
        return WhatsAppMessage(
            reminder_id=reminder.id,
            phone=phone,
            message=reminder.message,
            whatsapp_url=whatsapp_url(reminder.patient_phone, reminder.message),
        )

    # --- Apoyo ----------------------------------------------------------
    def _build_prescription_reminders(
        self,
        encounter: Encounter,
        prescription: Prescription,
        start: datetime,
        plan: ReminderPlan,
        actor: User,
    ) -> list[Reminder]:
        hours = prescription.frequency_hours
        days = prescription.duration_days
        if not hours or not days:
            return []

        doses = max(1, int((days * 24) / hours))
        step = timedelta(hours=hours)
        if doses > MAX_REMINDERS_PER_PRESCRIPTION:
            # Tratamiento prolongado: un aviso diario a la hora de la primera toma.
            doses = min(days, MAX_REMINDERS_PER_PRESCRIPTION)
            step = timedelta(days=1)

        title = f"Tomar {prescription.medication}"
        detail = prescription.schedule_label or prescription.medication
        message = (
            f"Hola {encounter.patient.display_name}, recuerde tomar "
            f"{prescription.medication} ({detail})."
        )
        if prescription.instructions:
            message = f"{message} {prescription.instructions}."

        return [
            Reminder(
                patient_id=encounter.patient_id,
                encounter_id=encounter.id,
                prescription_id=prescription.id,
                kind=ReminderKind.MEDICAMENTO.value,
                channel=plan.channel.value,
                status=ReminderStatus.PENDIENTE.value,
                title=title,
                message=message,
                scheduled_for=start + step * index,
                created_by_id=actor.id,
            )
            for index in range(doses)
        ]

    def _get_patient(self, patient_id: int):
        patient = self.patients.get_by_id(patient_id)
        if patient is None:
            raise BusinessRuleError("El paciente indicado no existe")
        return patient

from datetime import date

from sqlalchemy.orm import Session

from app.core.datetime import now, to_local
from app.models.appointment import Appointment, AppointmentStatus
from app.models.encounter import (
    Encounter,
    EncounterDiagnosis,
    EncounterStatus,
    Prescription,
)
from app.models.user import User
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.encounter_repository import EncounterRepository
from app.repositories.inventory_repository import ProductRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.practitioner_repository import PractitionerRepository
from app.schemas.common import Pagination
from app.schemas.encounter import (
    DiagnosisWrite,
    EncounterCreate,
    EncounterUpdate,
    PrescriptionWrite,
)
from app.services.exceptions import BusinessRuleError, ConflictError, NotFoundError

CLINICAL_FIELDS = (
    "service_id",
    "chief_complaint",
    "current_illness",
    "physical_exam",
    "treatment_plan",
    "indications",
    "observations",
    "systolic_pressure",
    "diastolic_pressure",
    "heart_rate",
    "respiratory_rate",
    "temperature",
    "oxygen_saturation",
    "weight_kg",
    "height_cm",
)


class EncounterService:
    """Atenciones médicas e historia clínica (cláusulas 2.2 y 2.3)."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.encounters = EncounterRepository(db)
        self.patients = PatientRepository(db)
        self.practitioners = PractitionerRepository(db)
        self.appointments = AppointmentRepository(db)
        self.products = ProductRepository(db)

    # --- Consultas ------------------------------------------------------
    def list_encounters(
        self,
        *,
        term: str | None = None,
        patient_id: int | None = None,
        practitioner_id: int | None = None,
        status: str | None = None,
        day: date | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        pagination: Pagination,
    ) -> tuple[list[Encounter], int]:
        return self.encounters.search(
            term=term,
            patient_id=patient_id,
            practitioner_id=practitioner_id,
            status=status,
            day=day,
            date_from=date_from,
            date_to=date_to,
            pagination=pagination,
        )

    def get(self, encounter_id: int) -> Encounter:
        encounter = self.encounters.get_by_id(encounter_id)
        if encounter is None:
            raise NotFoundError("La atención no existe")
        return encounter

    def history_for_patient(self, patient_id: int) -> list[Encounter]:
        return self.encounters.list_for_patient(patient_id)

    def record_summary(self, patient_id: int) -> tuple[int, Encounter | None]:
        return (
            self.encounters.count_for_patient(patient_id),
            self.encounters.last_for_patient(patient_id),
        )

    # --- Registro -------------------------------------------------------
    def create(self, payload: EncounterCreate, actor: User) -> Encounter:
        patient = self._get_patient(payload.patient_id)
        practitioner = self._get_practitioner(payload.practitioner_id)
        appointment = self._resolve_appointment(payload.appointment_id, patient.id, practitioner.id)

        encounter = Encounter(
            patient_id=patient.id,
            practitioner_id=practitioner.id,
            appointment_id=appointment.id if appointment else None,
            started_at=to_local(payload.started_at) if payload.started_at else now(),
            status=EncounterStatus.EN_CURSO.value,
            created_by_id=actor.id,
            **{field: getattr(payload, field) for field in CLINICAL_FIELDS},
        )
        encounter.diagnoses = self._build_diagnoses(payload.diagnoses)
        encounter.prescriptions = self._build_prescriptions(payload.prescriptions)

        created = self.encounters.add(encounter)
        if appointment is not None:
            self._mark_appointment_in_progress(appointment)
        return created

    def update(self, encounter_id: int, payload: EncounterUpdate) -> Encounter:
        encounter = self.get(encounter_id)
        self._ensure_editable(encounter)

        for field in CLINICAL_FIELDS:
            setattr(encounter, field, getattr(payload, field))
        if payload.diagnoses is not None:
            encounter.diagnoses = self._build_diagnoses(payload.diagnoses)
        if payload.prescriptions is not None:
            encounter.prescriptions = self._build_prescriptions(payload.prescriptions)

        return self.encounters.save(encounter)

    def finish(self, encounter_id: int) -> Encounter:
        encounter = self.get(encounter_id)
        self._ensure_editable(encounter)
        if not encounter.diagnoses:
            raise BusinessRuleError("Registre al menos un diagnóstico antes de finalizar")

        encounter.status = EncounterStatus.FINALIZADA.value
        encounter.finished_at = now()
        saved = self.encounters.save(encounter)

        if encounter.appointment_id is not None:
            appointment = self.appointments.get_by_id(encounter.appointment_id)
            if appointment is not None and appointment.status not in (
                AppointmentStatus.ATENDIDA.value,
                AppointmentStatus.CANCELADA.value,
            ):
                appointment.status = AppointmentStatus.ATENDIDA.value
                self.appointments.save(appointment)
        return saved

    def cancel(self, encounter_id: int, reason: str) -> Encounter:
        encounter = self.get(encounter_id)
        if encounter.status == EncounterStatus.ANULADA.value:
            return encounter
        if encounter.status == EncounterStatus.FINALIZADA.value:
            raise BusinessRuleError("Una atención finalizada no puede anularse")

        encounter.status = EncounterStatus.ANULADA.value
        encounter.finished_at = now()
        encounter.observations = _append_note(encounter.observations, f"Anulada: {reason}")
        return self.encounters.save(encounter)

    # --- Apoyo ----------------------------------------------------------
    @staticmethod
    def _ensure_editable(encounter: Encounter) -> None:
        if not encounter.is_editable:
            raise BusinessRuleError(
                f"La atención está {encounter.status_label.lower()} y ya no admite cambios"
            )

    @staticmethod
    def _build_diagnoses(items: list[DiagnosisWrite]) -> list[EncounterDiagnosis]:
        return [
            EncounterDiagnosis(
                code=item.code, description=item.description, kind=item.kind.value
            )
            for item in items
        ]

    def _build_prescriptions(self, items: list[PrescriptionWrite]) -> list[Prescription]:
        prescriptions: list[Prescription] = []
        for item in items:
            if item.product_id is not None and self.products.get_by_id(item.product_id) is None:
                raise BusinessRuleError("El producto indicado en la receta no existe")
            prescriptions.append(Prescription(**item.model_dump()))
        return prescriptions

    def _resolve_appointment(
        self, appointment_id: int | None, patient_id: int, practitioner_id: int
    ) -> Appointment | None:
        if appointment_id is None:
            return None
        appointment = self.appointments.get_by_id(appointment_id)
        if appointment is None:
            raise BusinessRuleError("La cita indicada no existe")
        if appointment.patient_id != patient_id or appointment.practitioner_id != practitioner_id:
            raise BusinessRuleError("La cita no corresponde al paciente y profesional indicados")
        if self.encounters.get_by_appointment(appointment_id) is not None:
            raise ConflictError("Esa cita ya tiene una atención registrada")
        return appointment

    def _mark_appointment_in_progress(self, appointment: Appointment) -> None:
        if appointment.status in (
            AppointmentStatus.PROGRAMADA.value,
            AppointmentStatus.CONFIRMADA.value,
        ):
            appointment.status = AppointmentStatus.EN_ATENCION.value
            self.appointments.save(appointment)

    def _get_patient(self, patient_id: int):
        patient = self.patients.get_by_id(patient_id)
        if patient is None:
            raise BusinessRuleError("El paciente indicado no existe")
        return patient

    def _get_practitioner(self, practitioner_id: int):
        practitioner = self.practitioners.get_by_id(practitioner_id)
        if practitioner is None:
            raise BusinessRuleError("El profesional indicado no existe")
        if not practitioner.is_active:
            raise BusinessRuleError("El profesional se encuentra inactivo")
        return practitioner


def _append_note(current: str | None, note: str) -> str:
    return f"{current}\n{note}" if current else note

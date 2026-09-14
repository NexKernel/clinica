from sqlalchemy.orm import Session

from app.core.datetime import today
from app.models.patient import DocumentType, Patient
from app.repositories.patient_repository import PatientRepository
from app.schemas.common import Pagination
from app.schemas.patient import PatientCreate, PatientStats, PatientUpdate
from app.services.exceptions import ConflictError, NotFoundError


class PatientService:
    """Padrón de pacientes e historia clínica básica (cláusula 2.2)."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.patients = PatientRepository(db)

    def list_patients(
        self, *, term: str | None, is_active: bool | None, pagination: Pagination
    ) -> tuple[list[Patient], int]:
        return self.patients.search(term=term, is_active=is_active, pagination=pagination)

    def quick_search(self, term: str) -> list[Patient]:
        if not term or len(term.strip()) < 2:
            return []
        return self.patients.quick_search(term)

    def get(self, patient_id: int) -> Patient:
        """Ficha por id interno; para uso entre módulos, no desde una URL."""
        patient = self.patients.get_by_id(patient_id)
        if patient is None:
            raise NotFoundError("El paciente no existe")
        return patient

    def get_public(self, public_id: str) -> Patient:
        """Ficha por identificador opaco: la única vía que abren las rutas de
        `/patients/{...}`, para que un correlativo no permita recorrer el
        padrón probando /pacientes/1, /pacientes/2..."""
        patient = self.patients.get_by_public_id(public_id)
        if patient is None:
            raise NotFoundError("El paciente no existe")
        return patient

    def find_by_document(self, document_type: str, document_number: str) -> Patient | None:
        return self.patients.get_by_document(document_type, document_number)

    def create(self, payload: PatientCreate) -> Patient:
        self._ensure_document_available(payload.document_type, payload.document_number)
        patient = Patient(
            history_number=self.patients.next_history_number(),
            **self._writable_fields(payload),
        )
        return self.patients.add(patient)

    def update(self, public_id: str, payload: PatientUpdate) -> Patient:
        patient = self.get_public(public_id)
        self._ensure_document_available(
            payload.document_type, payload.document_number, exclude_id=patient.id
        )
        for field, value in self._writable_fields(payload).items():
            setattr(patient, field, value)
        return self.patients.save(patient)

    def set_active(self, public_id: str, is_active: bool) -> Patient:
        patient = self.get_public(public_id)
        patient.is_active = is_active
        return self.patients.save(patient)

    def stats(self) -> PatientStats:
        reference = today()
        return PatientStats(
            total=self.patients.count_all(),
            active=self.patients.count_all(is_active=True),
            registered_today=self.patients.count_registered_today(),
            registered_this_month=self.patients.count_registered_since(reference.replace(day=1)),
        )

    @staticmethod
    def _writable_fields(payload: PatientCreate | PatientUpdate) -> dict[str, object]:
        data = payload.model_dump()
        data["document_type"] = payload.document_type.value
        data["sex"] = payload.sex.value if payload.sex else None
        data["email"] = str(payload.email) if payload.email else None
        return data

    def _ensure_document_available(
        self,
        document_type: DocumentType,
        document_number: str | None,
        exclude_id: int | None = None,
    ) -> None:
        if document_type is DocumentType.SIN_DOCUMENTO or not document_number:
            return
        if self.patients.document_taken(
            document_type.value, document_number, exclude_id=exclude_id
        ):
            raise ConflictError("Ya existe un paciente registrado con ese documento")

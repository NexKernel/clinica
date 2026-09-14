from sqlalchemy.orm import Session

from app.models.catalog import MedicalService, Specialty
from app.repositories.catalog_repository import MedicalServiceRepository, SpecialtyRepository
from app.schemas.catalog import (
    MedicalServiceCreate,
    MedicalServiceUpdate,
    SpecialtyCreate,
    SpecialtyUpdate,
)
from app.schemas.common import Pagination
from app.services.exceptions import ConflictError, NotFoundError


class CatalogService:
    """Especialidades y tarifario de servicios del policlínico."""

    def __init__(self, db: Session) -> None:
        self.specialties = SpecialtyRepository(db)
        self.services = MedicalServiceRepository(db)

    # --- Especialidades -------------------------------------------------
    def list_specialties(self, *, only_active: bool = False) -> list[Specialty]:
        return self.specialties.list_all(only_active=only_active)

    def get_specialty(self, specialty_id: int) -> Specialty:
        specialty = self.specialties.get_by_id(specialty_id)
        if specialty is None:
            raise NotFoundError("La especialidad no existe")
        return specialty

    def create_specialty(self, payload: SpecialtyCreate) -> Specialty:
        if self.specialties.name_taken(payload.name):
            raise ConflictError("Ya existe una especialidad con ese nombre")
        return self.specialties.add(Specialty(**payload.model_dump()))

    def update_specialty(self, specialty_id: int, payload: SpecialtyUpdate) -> Specialty:
        specialty = self.get_specialty(specialty_id)
        if self.specialties.name_taken(payload.name, exclude_id=specialty.id):
            raise ConflictError("Ya existe una especialidad con ese nombre")
        for field, value in payload.model_dump().items():
            setattr(specialty, field, value)
        return self.specialties.save(specialty)

    # --- Tarifario ------------------------------------------------------
    def list_services(
        self,
        *,
        term: str | None,
        kind: str | None,
        specialty_id: int | None,
        is_active: bool | None,
        pagination: Pagination,
    ) -> tuple[list[MedicalService], int]:
        return self.services.search(
            term=term,
            kind=kind,
            specialty_id=specialty_id,
            is_active=is_active,
            pagination=pagination,
        )

    def list_active_services(self) -> list[MedicalService]:
        return self.services.list_active()

    def get_service(self, service_id: int) -> MedicalService:
        service = self.services.get_by_id(service_id)
        if service is None:
            raise NotFoundError("El servicio no existe")
        return service

    def create_service(self, payload: MedicalServiceCreate) -> MedicalService:
        self._validate_service(payload)
        if self.services.code_taken(payload.code):
            raise ConflictError("Ya existe un servicio con ese código")
        return self.services.add(MedicalService(**self._service_fields(payload)))

    def update_service(self, service_id: int, payload: MedicalServiceUpdate) -> MedicalService:
        service = self.get_service(service_id)
        self._validate_service(payload)
        if self.services.code_taken(payload.code, exclude_id=service.id):
            raise ConflictError("Ya existe un servicio con ese código")
        for field, value in self._service_fields(payload).items():
            setattr(service, field, value)
        return self.services.save(service)

    def _validate_service(self, payload: MedicalServiceCreate | MedicalServiceUpdate) -> None:
        if payload.specialty_id is not None:
            self.get_specialty(payload.specialty_id)

    @staticmethod
    def _service_fields(
        payload: MedicalServiceCreate | MedicalServiceUpdate,
    ) -> dict[str, object]:
        data = payload.model_dump()
        data["kind"] = payload.kind.value
        return data

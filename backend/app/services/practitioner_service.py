from sqlalchemy.orm import Session

from app.models.practitioner import Practitioner, PractitionerSchedule
from app.repositories.catalog_repository import SpecialtyRepository
from app.repositories.practitioner_repository import PractitionerRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import Pagination
from app.schemas.practitioner import PractitionerCreate, PractitionerUpdate, ScheduleWrite
from app.services.exceptions import BusinessRuleError, ConflictError, NotFoundError


class PractitionerService:
    """Profesionales y su agenda semanal de atención."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.practitioners = PractitionerRepository(db)
        self.specialties = SpecialtyRepository(db)
        self.users = UserRepository(db)

    def list_practitioners(
        self,
        *,
        term: str | None,
        specialty_id: int | None,
        is_active: bool | None,
        pagination: Pagination,
    ) -> tuple[list[Practitioner], int]:
        return self.practitioners.search(
            term=term, specialty_id=specialty_id, is_active=is_active, pagination=pagination
        )

    def list_active(self) -> list[Practitioner]:
        return self.practitioners.list_active()

    def get(self, practitioner_id: int) -> Practitioner:
        practitioner = self.practitioners.get_by_id(practitioner_id)
        if practitioner is None:
            raise NotFoundError("El profesional no existe")
        return practitioner

    def get_for_user(self, user_id: int) -> Practitioner | None:
        return self.practitioners.get_by_user(user_id)

    def create(self, payload: PractitionerCreate) -> Practitioner:
        self._validate_references(payload.specialty_id, payload.user_id)
        practitioner = Practitioner(
            **payload.model_dump(exclude={"schedules"}, exclude_none=False)
            | {"email": str(payload.email) if payload.email else None}
        )
        practitioner.schedules = self._build_schedules(payload.schedules)
        return self.practitioners.add(practitioner)

    def update(self, practitioner_id: int, payload: PractitionerUpdate) -> Practitioner:
        practitioner = self.get(practitioner_id)
        self._validate_references(payload.specialty_id, payload.user_id, exclude_id=practitioner.id)

        data = payload.model_dump(exclude={"schedules"})
        data["email"] = str(payload.email) if payload.email else None
        for field, value in data.items():
            setattr(practitioner, field, value)

        if payload.schedules is not None:
            practitioner.schedules = self._build_schedules(payload.schedules)

        return self.practitioners.save(practitioner)

    def set_active(self, practitioner_id: int, is_active: bool) -> Practitioner:
        practitioner = self.get(practitioner_id)
        practitioner.is_active = is_active
        return self.practitioners.save(practitioner)

    def _validate_references(
        self, specialty_id: int | None, user_id: int | None, exclude_id: int | None = None
    ) -> None:
        if specialty_id is not None and self.specialties.get_by_id(specialty_id) is None:
            raise BusinessRuleError("La especialidad indicada no existe")
        if user_id is not None:
            if self.users.get_by_id(user_id) is None:
                raise BusinessRuleError("El usuario indicado no existe")
            if self.practitioners.user_taken(user_id, exclude_id=exclude_id):
                raise ConflictError("Ese usuario ya está vinculado a otro profesional")

    @staticmethod
    def _build_schedules(blocks: list[ScheduleWrite]) -> list[PractitionerSchedule]:
        ordered = sorted(blocks, key=lambda block: (block.weekday, block.start_time))
        for previous, current in zip(ordered, ordered[1:]):
            if previous.weekday == current.weekday and current.start_time < previous.end_time:
                raise BusinessRuleError(
                    "Los bloques horarios de un mismo día no pueden superponerse"
                )
        return [PractitionerSchedule(**block.model_dump()) for block in ordered]

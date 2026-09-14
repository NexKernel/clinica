from sqlalchemy import Select, func, or_, select

from app.models.catalog import MedicalService, Specialty
from app.repositories.base import BaseRepository
from app.schemas.common import Pagination


class SpecialtyRepository(BaseRepository[Specialty]):
    model = Specialty

    def list_all(self, *, only_active: bool = False) -> list[Specialty]:
        stmt = select(Specialty).order_by(Specialty.name)
        if only_active:
            stmt = stmt.where(Specialty.is_active.is_(True))
        return list(self.db.execute(stmt).scalars().all())

    def name_taken(self, name: str, exclude_id: int | None = None) -> bool:
        stmt = select(Specialty.id).where(func.lower(Specialty.name) == name.strip().lower())
        if exclude_id is not None:
            stmt = stmt.where(Specialty.id != exclude_id)
        return self.db.execute(stmt).first() is not None


class MedicalServiceRepository(BaseRepository[MedicalService]):
    model = MedicalService

    def code_taken(self, code: str, exclude_id: int | None = None) -> bool:
        stmt = select(MedicalService.id).where(
            func.upper(MedicalService.code) == code.strip().upper()
        )
        if exclude_id is not None:
            stmt = stmt.where(MedicalService.id != exclude_id)
        return self.db.execute(stmt).first() is not None

    def search(
        self,
        *,
        term: str | None = None,
        kind: str | None = None,
        specialty_id: int | None = None,
        is_active: bool | None = None,
        pagination: Pagination,
    ) -> tuple[list[MedicalService], int]:
        stmt = self._apply_filters(
            select(MedicalService), term, kind, specialty_id, is_active
        ).order_by(MedicalService.name)
        return self.paginate(stmt, pagination)

    def list_active(self) -> list[MedicalService]:
        stmt = (
            select(MedicalService)
            .where(MedicalService.is_active.is_(True))
            .order_by(MedicalService.name)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    @staticmethod
    def _apply_filters(
        stmt: Select[tuple[MedicalService]],
        term: str | None,
        kind: str | None,
        specialty_id: int | None,
        is_active: bool | None,
    ) -> Select[tuple[MedicalService]]:
        if term:
            pattern = f"%{term.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(MedicalService.name).like(pattern),
                    func.lower(MedicalService.code).like(pattern),
                )
            )
        if kind:
            stmt = stmt.where(MedicalService.kind == kind)
        if specialty_id is not None:
            stmt = stmt.where(MedicalService.specialty_id == specialty_id)
        if is_active is not None:
            stmt = stmt.where(MedicalService.is_active.is_(is_active))
        return stmt

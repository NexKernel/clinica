from sqlalchemy import Select, func, or_, select

from app.models.practitioner import Practitioner
from app.repositories.base import BaseRepository
from app.schemas.common import Pagination


class PractitionerRepository(BaseRepository[Practitioner]):
    model = Practitioner

    def get_by_user(self, user_id: int) -> Practitioner | None:
        stmt = select(Practitioner).where(Practitioner.user_id == user_id)
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def user_taken(self, user_id: int, exclude_id: int | None = None) -> bool:
        stmt = select(Practitioner.id).where(Practitioner.user_id == user_id)
        if exclude_id is not None:
            stmt = stmt.where(Practitioner.id != exclude_id)
        return self.db.execute(stmt).first() is not None

    def search(
        self,
        *,
        term: str | None = None,
        specialty_id: int | None = None,
        is_active: bool | None = None,
        pagination: Pagination,
    ) -> tuple[list[Practitioner], int]:
        stmt = self._apply_filters(select(Practitioner), term, specialty_id, is_active).order_by(
            Practitioner.full_name
        )
        return self.paginate(stmt, pagination)

    def list_active(self) -> list[Practitioner]:
        stmt = (
            select(Practitioner)
            .where(Practitioner.is_active.is_(True))
            .order_by(Practitioner.full_name)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    @staticmethod
    def _apply_filters(
        stmt: Select[tuple[Practitioner]],
        term: str | None,
        specialty_id: int | None,
        is_active: bool | None,
    ) -> Select[tuple[Practitioner]]:
        if term:
            pattern = f"%{term.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Practitioner.full_name).like(pattern),
                    func.lower(Practitioner.license_number).like(pattern),
                )
            )
        if specialty_id is not None:
            stmt = stmt.where(Practitioner.specialty_id == specialty_id)
        if is_active is not None:
            stmt = stmt.where(Practitioner.is_active.is_(is_active))
        return stmt

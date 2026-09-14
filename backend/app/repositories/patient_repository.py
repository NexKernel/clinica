from datetime import date

from sqlalchemy import Select, func, or_, select

from app.core.datetime import today
from app.models.patient import Patient
from app.repositories.base import BaseRepository
from app.schemas.common import Pagination

HISTORY_PREFIX = "HC"
HISTORY_DIGITS = 6


class PatientRepository(BaseRepository[Patient]):
    model = Patient

    def get_by_public_id(self, public_id: str) -> Patient | None:
        stmt = select(Patient).where(Patient.public_id == public_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_document(self, document_type: str, document_number: str) -> Patient | None:
        stmt = select(Patient).where(
            Patient.document_type == document_type,
            Patient.document_number == document_number,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def document_taken(
        self, document_type: str, document_number: str, exclude_id: int | None = None
    ) -> bool:
        stmt = select(Patient.id).where(
            Patient.document_type == document_type,
            Patient.document_number == document_number,
        )
        if exclude_id is not None:
            stmt = stmt.where(Patient.id != exclude_id)
        return self.db.execute(stmt).first() is not None

    def next_history_number(self) -> str:
        """Correlativo de historia clínica: HC-000001."""
        last = self.db.execute(select(func.max(Patient.id))).scalar_one_or_none() or 0
        return f"{HISTORY_PREFIX}-{last + 1:0{HISTORY_DIGITS}d}"

    def search(
        self,
        *,
        term: str | None = None,
        is_active: bool | None = None,
        pagination: Pagination,
    ) -> tuple[list[Patient], int]:
        stmt = self._apply_filters(select(Patient), term, is_active).order_by(
            Patient.last_name_paternal, Patient.last_name_maternal, Patient.first_name
        )
        return self.paginate(stmt, pagination)

    def quick_search(self, term: str, limit: int = 10) -> list[Patient]:
        """Búsqueda incremental para los selectores de citas, caja y consultas."""
        stmt = (
            self._apply_filters(select(Patient), term, is_active=True)
            .order_by(Patient.last_name_paternal, Patient.first_name)
            .limit(limit)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def count_all(self, *, is_active: bool | None = None) -> int:
        stmt = select(func.count(Patient.id))
        if is_active is not None:
            stmt = stmt.where(Patient.is_active.is_(is_active))
        return self.db.execute(stmt).scalar_one()

    def count_registered_since(self, since: date) -> int:
        stmt = select(func.count(Patient.id)).where(func.date(Patient.created_at) >= since)
        return self.db.execute(stmt).scalar_one()

    def count_registered_today(self) -> int:
        return self.count_registered_since(today())

    @staticmethod
    def _apply_filters(
        stmt: Select[tuple[Patient]], term: str | None, is_active: bool | None
    ) -> Select[tuple[Patient]]:
        if term:
            pattern = f"%{term.strip().lower()}%"
            # Concatenación con el operador estándar (||) para no depender del motor.
            full_name = func.lower(
                Patient.last_name_paternal
                + " "
                + func.coalesce(Patient.last_name_maternal, "")
                + " "
                + Patient.first_name
            )
            stmt = stmt.where(
                or_(
                    full_name.like(pattern),
                    func.lower(Patient.first_name).like(pattern),
                    func.lower(Patient.document_number).like(pattern),
                    func.lower(Patient.history_number).like(pattern),
                    func.lower(Patient.phone).like(pattern),
                )
            )
        if is_active is not None:
            stmt = stmt.where(Patient.is_active.is_(is_active))
        return stmt

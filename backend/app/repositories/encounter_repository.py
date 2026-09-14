from datetime import date

from sqlalchemy import Select, func, or_, select

from app.core.datetime import as_date, end_of_day, start_of_day
from app.models.encounter import Encounter, EncounterStatus
from app.models.patient import Patient
from app.repositories.base import BaseRepository
from app.schemas.common import Pagination


class EncounterRepository(BaseRepository[Encounter]):
    model = Encounter

    def get_by_appointment(self, appointment_id: int) -> Encounter | None:
        stmt = select(Encounter).where(Encounter.appointment_id == appointment_id)
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def get_open_for_practitioner(self, practitioner_id: int) -> list[Encounter]:
        stmt = (
            select(Encounter)
            .where(
                Encounter.practitioner_id == practitioner_id,
                Encounter.status == EncounterStatus.EN_CURSO.value,
            )
            .order_by(Encounter.started_at)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def search(
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
        stmt = self._apply_filters(
            select(Encounter).join(Encounter.patient),
            term=term,
            patient_id=patient_id,
            practitioner_id=practitioner_id,
            status=status,
            day=day,
            date_from=date_from,
            date_to=date_to,
        ).order_by(Encounter.started_at.desc())
        return self.paginate(stmt, pagination)

    def list_for_patient(self, patient_id: int, limit: int = 100) -> list[Encounter]:
        stmt = (
            select(Encounter)
            .where(Encounter.patient_id == patient_id)
            .order_by(Encounter.started_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def count_for_patient(self, patient_id: int) -> int:
        stmt = select(func.count(Encounter.id)).where(Encounter.patient_id == patient_id)
        return self.db.execute(stmt).scalar_one()

    def last_for_patient(self, patient_id: int) -> Encounter | None:
        stmt = (
            select(Encounter)
            .where(Encounter.patient_id == patient_id)
            .order_by(Encounter.started_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).unique().scalars().first()

    def count_in_range(self, date_from: date, date_to: date, status: str | None = None) -> int:
        stmt = select(func.count(Encounter.id)).where(
            Encounter.started_at.between(start_of_day(date_from), end_of_day(date_to))
        )
        if status:
            stmt = stmt.where(Encounter.status == status)
        return self.db.execute(stmt).scalar_one()

    def daily_counts(self, date_from: date, date_to: date) -> list[tuple[date, int]]:
        """Atenciones por día, para los indicadores del dashboard."""
        day = func.date(Encounter.started_at)
        stmt = (
            select(day, func.count(Encounter.id))
            .where(Encounter.started_at.between(start_of_day(date_from), end_of_day(date_to)))
            .group_by(day)
            .order_by(day)
        )
        return [(as_date(value), count) for value, count in self.db.execute(stmt).all()]

    @staticmethod
    def _apply_filters(
        stmt: Select[tuple[Encounter]],
        *,
        term: str | None,
        patient_id: int | None,
        practitioner_id: int | None,
        status: str | None,
        day: date | None,
        date_from: date | None,
        date_to: date | None,
    ) -> Select[tuple[Encounter]]:
        if term:
            pattern = f"%{term.strip().lower()}%"
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
                    func.lower(Patient.document_number).like(pattern),
                    func.lower(Patient.history_number).like(pattern),
                )
            )
        if patient_id is not None:
            stmt = stmt.where(Encounter.patient_id == patient_id)
        if practitioner_id is not None:
            stmt = stmt.where(Encounter.practitioner_id == practitioner_id)
        if status:
            stmt = stmt.where(Encounter.status == status)
        if day is not None:
            stmt = stmt.where(Encounter.started_at.between(start_of_day(day), end_of_day(day)))
        else:
            if date_from is not None:
                stmt = stmt.where(Encounter.started_at >= start_of_day(date_from))
            if date_to is not None:
                stmt = stmt.where(Encounter.started_at <= end_of_day(date_to))
        return stmt

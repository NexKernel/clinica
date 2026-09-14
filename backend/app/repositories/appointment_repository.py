from datetime import date, datetime, timedelta

from sqlalchemy import Select, and_, func, or_, select

from app.core.datetime import end_of_day, start_of_day, to_local
from app.models.appointment import BLOCKING_STATUSES, Appointment
from app.models.patient import Patient
from app.repositories.base import BaseRepository
from app.schemas.common import Pagination


class AppointmentRepository(BaseRepository[Appointment]):
    model = Appointment

    def search(
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
        stmt = self._apply_filters(
            select(Appointment).join(Appointment.patient),
            term=term,
            practitioner_id=practitioner_id,
            patient_id=patient_id,
            status=status,
            day=day,
            date_from=date_from,
            date_to=date_to,
        ).order_by(Appointment.scheduled_at.desc())
        return self.paginate(stmt, pagination)

    def list_for_day(self, day: date, practitioner_id: int | None = None) -> list[Appointment]:
        stmt = (
            select(Appointment)
            .where(Appointment.scheduled_at.between(start_of_day(day), end_of_day(day)))
            .order_by(Appointment.scheduled_at)
        )
        if practitioner_id is not None:
            stmt = stmt.where(Appointment.practitioner_id == practitioner_id)
        return list(self.db.execute(stmt).unique().scalars().all())

    def list_in_range(
        self, date_from: date, date_to: date, practitioner_id: int | None = None
    ) -> list[Appointment]:
        """Citas de un rango de días, ordenadas por hora.

        La vista de calendario pinta la semana o el mes completos, así que
        necesita el rango entero de una sola consulta y no paginado.
        """
        stmt = (
            select(Appointment)
            .where(Appointment.scheduled_at.between(start_of_day(date_from), end_of_day(date_to)))
            .order_by(Appointment.scheduled_at)
        )
        if practitioner_id is not None:
            stmt = stmt.where(Appointment.practitioner_id == practitioner_id)
        return list(self.db.execute(stmt).unique().scalars().all())

    def list_for_patient(self, patient_id: int, limit: int = 50) -> list[Appointment]:
        stmt = (
            select(Appointment)
            .where(Appointment.patient_id == patient_id)
            .order_by(Appointment.scheduled_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def find_overlap(
        self,
        *,
        practitioner_id: int,
        start: datetime,
        end: datetime,
        exclude_id: int | None = None,
    ) -> Appointment | None:
        """Cita que ya ocupa ese espacio en la agenda del profesional.

        Se acotan las candidatas al día de la cita y el cruce por duración se
        resuelve en Python, para no depender de funciones de intervalo propias
        de cada motor de base de datos.
        """
        stmt = select(Appointment).where(
            Appointment.practitioner_id == practitioner_id,
            Appointment.status.in_(BLOCKING_STATUSES),
            Appointment.scheduled_at.between(start_of_day(start.date()), end_of_day(end.date())),
            Appointment.scheduled_at < end,
        )
        if exclude_id is not None:
            stmt = stmt.where(Appointment.id != exclude_id)

        for candidate in self.db.execute(stmt).unique().scalars().all():
            candidate_start = to_local(candidate.scheduled_at)
            candidate_end = candidate_start + timedelta(minutes=candidate.duration_minutes)
            if candidate_end > start:
                return candidate
        return None

    def count_by_status(self, day: date, practitioner_id: int | None = None) -> dict[str, int]:
        stmt = (
            select(Appointment.status, func.count(Appointment.id))
            .where(Appointment.scheduled_at.between(start_of_day(day), end_of_day(day)))
            .group_by(Appointment.status)
        )
        if practitioner_id is not None:
            stmt = stmt.where(Appointment.practitioner_id == practitioner_id)
        return {status: count for status, count in self.db.execute(stmt).all()}

    def count_in_range(
        self, *, date_from: date, date_to: date, statuses: tuple[str, ...] | None = None
    ) -> int:
        stmt = select(func.count(Appointment.id)).where(
            Appointment.scheduled_at.between(start_of_day(date_from), end_of_day(date_to))
        )
        if statuses:
            stmt = stmt.where(Appointment.status.in_(statuses))
        return self.db.execute(stmt).scalar_one()

    def upcoming_for_patient(self, patient_id: int, reference: datetime) -> list[Appointment]:
        stmt = (
            select(Appointment)
            .where(
                Appointment.patient_id == patient_id,
                Appointment.scheduled_at >= reference,
                Appointment.status.in_(BLOCKING_STATUSES),
            )
            .order_by(Appointment.scheduled_at)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    @staticmethod
    def _apply_filters(
        stmt: Select[tuple[Appointment]],
        *,
        term: str | None,
        practitioner_id: int | None,
        patient_id: int | None,
        status: str | None,
        day: date | None,
        date_from: date | None,
        date_to: date | None,
    ) -> Select[tuple[Appointment]]:
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
        if practitioner_id is not None:
            stmt = stmt.where(Appointment.practitioner_id == practitioner_id)
        if patient_id is not None:
            stmt = stmt.where(Appointment.patient_id == patient_id)
        if status:
            stmt = stmt.where(Appointment.status == status)
        if day is not None:
            stmt = stmt.where(Appointment.scheduled_at.between(start_of_day(day), end_of_day(day)))
        elif date_from is not None or date_to is not None:
            conditions = []
            if date_from is not None:
                conditions.append(Appointment.scheduled_at >= start_of_day(date_from))
            if date_to is not None:
                conditions.append(Appointment.scheduled_at <= end_of_day(date_to))
            stmt = stmt.where(and_(*conditions))
        return stmt

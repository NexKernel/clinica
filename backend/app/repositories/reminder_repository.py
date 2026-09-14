from datetime import date, datetime

from sqlalchemy import func, select

from app.core.datetime import end_of_day, start_of_day
from app.models.reminder import Reminder, ReminderStatus
from app.repositories.base import BaseRepository
from app.schemas.common import Pagination


class ReminderRepository(BaseRepository[Reminder]):
    model = Reminder

    def search(
        self,
        *,
        patient_id: int | None = None,
        kind: str | None = None,
        status: str | None = None,
        channel: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        pagination: Pagination,
    ) -> tuple[list[Reminder], int]:
        stmt = select(Reminder)
        if patient_id is not None:
            stmt = stmt.where(Reminder.patient_id == patient_id)
        if kind:
            stmt = stmt.where(Reminder.kind == kind)
        if status:
            stmt = stmt.where(Reminder.status == status)
        if channel:
            stmt = stmt.where(Reminder.channel == channel)
        if date_from is not None:
            stmt = stmt.where(Reminder.scheduled_for >= start_of_day(date_from))
        if date_to is not None:
            stmt = stmt.where(Reminder.scheduled_for <= end_of_day(date_to))
        stmt = stmt.order_by(Reminder.scheduled_for, Reminder.id)
        return self.paginate(stmt, pagination)

    def list_pending_until(self, moment: datetime, limit: int = 100) -> list[Reminder]:
        """Recordatorios pendientes cuya hora ya llegó o llega hoy."""
        stmt = (
            select(Reminder)
            .where(
                Reminder.status == ReminderStatus.PENDIENTE.value,
                Reminder.scheduled_for <= moment,
            )
            .order_by(Reminder.scheduled_for)
            .limit(limit)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def count_pending_between(self, since: datetime, until: datetime) -> int:
        stmt = select(func.count(Reminder.id)).where(
            Reminder.status == ReminderStatus.PENDIENTE.value,
            Reminder.scheduled_for.between(since, until),
        )
        return self.db.execute(stmt).scalar_one()

    def count_overdue(self, moment: datetime) -> int:
        stmt = select(func.count(Reminder.id)).where(
            Reminder.status == ReminderStatus.PENDIENTE.value,
            Reminder.scheduled_for < moment,
        )
        return self.db.execute(stmt).scalar_one()

    def count_sent_on(self, day: date) -> int:
        stmt = select(func.count(Reminder.id)).where(
            Reminder.status == ReminderStatus.ENVIADO.value,
            Reminder.sent_at.between(start_of_day(day), end_of_day(day)),
        )
        return self.db.execute(stmt).scalar_one()

    def add_many(self, reminders: list[Reminder]) -> list[Reminder]:
        self.db.add_all(reminders)
        self.db.commit()
        for reminder in reminders:
            self.db.refresh(reminder)
        return reminders

    def delete_pending_for_prescription(self, prescription_id: int) -> int:
        stmt = select(Reminder).where(
            Reminder.prescription_id == prescription_id,
            Reminder.status == ReminderStatus.PENDIENTE.value,
        )
        pending = list(self.db.execute(stmt).unique().scalars().all())
        for reminder in pending:
            self.db.delete(reminder)
        if pending:
            self.db.commit()
        return len(pending)

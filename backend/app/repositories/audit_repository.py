from datetime import date

from sqlalchemy import func, or_, select

from app.core.datetime import end_of_day, start_of_day
from app.models.audit import AuditLog
from app.repositories.base import BaseRepository
from app.schemas.common import Pagination


class AuditRepository(BaseRepository[AuditLog]):
    model = AuditLog

    def search(
        self,
        *,
        term: str | None = None,
        user_id: int | None = None,
        module: str | None = None,
        action: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        pagination: Pagination,
    ) -> tuple[list[AuditLog], int]:
        stmt = select(AuditLog)
        if term:
            pattern = f"%{term.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(AuditLog.username).like(pattern),
                    func.lower(AuditLog.module).like(pattern),
                    func.lower(AuditLog.path).like(pattern),
                )
            )
        if user_id is not None:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if module:
            stmt = stmt.where(AuditLog.module == module)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if date_from is not None:
            stmt = stmt.where(AuditLog.created_at >= start_of_day(date_from))
        if date_to is not None:
            stmt = stmt.where(AuditLog.created_at <= end_of_day(date_to))
        stmt = stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        return self.paginate(stmt, pagination)

    def list_modules(self) -> list[str]:
        stmt = select(AuditLog.module).distinct().order_by(AuditLog.module)
        return list(self.db.execute(stmt).scalars().all())

from datetime import date

from sqlalchemy import Select, func, or_, select

from app.core.datetime import as_date, end_of_day, start_of_day
from app.models.sale import DocumentSeries, Sale, SaleStatus
from app.repositories.base import BaseRepository
from app.schemas.common import Pagination


class DocumentSeriesRepository(BaseRepository[DocumentSeries]):
    model = DocumentSeries

    def list_all(self, *, only_active: bool = False) -> list[DocumentSeries]:
        stmt = select(DocumentSeries).order_by(DocumentSeries.document_type, DocumentSeries.series)
        if only_active:
            stmt = stmt.where(DocumentSeries.is_active.is_(True))
        return list(self.db.execute(stmt).scalars().all())

    def get_by_series(self, document_type: str, series: str) -> DocumentSeries | None:
        stmt = select(DocumentSeries).where(
            DocumentSeries.document_type == document_type,
            func.upper(DocumentSeries.series) == series.strip().upper(),
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_default(self, document_type: str) -> DocumentSeries | None:
        stmt = (
            select(DocumentSeries)
            .where(
                DocumentSeries.document_type == document_type,
                DocumentSeries.is_active.is_(True),
            )
            .order_by(DocumentSeries.is_default.desc(), DocumentSeries.id)
            .limit(1)
        )
        return self.db.execute(stmt).scalars().first()

    def clear_default(self, document_type: str, keep_id: int | None = None) -> None:
        stmt = select(DocumentSeries).where(
            DocumentSeries.document_type == document_type,
            DocumentSeries.is_default.is_(True),
        )
        for item in self.db.execute(stmt).scalars().all():
            if keep_id is None or item.id != keep_id:
                item.is_default = False
                self.db.add(item)


class SaleRepository(BaseRepository[Sale]):
    model = Sale

    def search(
        self,
        *,
        term: str | None = None,
        document_type: str | None = None,
        status: str | None = None,
        patient_id: int | None = None,
        payment_method: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        pagination: Pagination,
    ) -> tuple[list[Sale], int]:
        stmt = self._apply_filters(
            select(Sale),
            term=term,
            document_type=document_type,
            status=status,
            patient_id=patient_id,
            payment_method=payment_method,
            date_from=date_from,
            date_to=date_to,
        ).order_by(Sale.issued_at.desc(), Sale.id.desc())
        return self.paginate(stmt, pagination)

    def list_in_range(self, date_from: date, date_to: date) -> list[Sale]:
        stmt = (
            select(Sale)
            .where(Sale.issued_at.between(start_of_day(date_from), end_of_day(date_to)))
            .order_by(Sale.issued_at)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def revenue_in_range(self, date_from: date, date_to: date) -> float:
        stmt = select(func.coalesce(func.sum(Sale.total), 0)).where(
            Sale.status == SaleStatus.EMITIDA.value,
            Sale.issued_at.between(start_of_day(date_from), end_of_day(date_to)),
        )
        return float(self.db.execute(stmt).scalar_one())

    def daily_revenue(self, date_from: date, date_to: date) -> list[tuple[date, float]]:
        """Ingresos por día, para los indicadores del dashboard."""
        day = func.date(Sale.issued_at)
        stmt = (
            select(day, func.coalesce(func.sum(Sale.total), 0))
            .where(
                Sale.status == SaleStatus.EMITIDA.value,
                Sale.issued_at.between(start_of_day(date_from), end_of_day(date_to)),
            )
            .group_by(day)
            .order_by(day)
        )
        return [(as_date(value), float(total)) for value, total in self.db.execute(stmt).all()]

    def count_in_range(self, date_from: date, date_to: date, status: str | None = None) -> int:
        stmt = select(func.count(Sale.id)).where(
            Sale.issued_at.between(start_of_day(date_from), end_of_day(date_to))
        )
        if status:
            stmt = stmt.where(Sale.status == status)
        return self.db.execute(stmt).scalar_one()

    @staticmethod
    def _apply_filters(
        stmt: Select[tuple[Sale]],
        *,
        term: str | None,
        document_type: str | None,
        status: str | None,
        patient_id: int | None,
        payment_method: str | None,
        date_from: date | None,
        date_to: date | None,
    ) -> Select[tuple[Sale]]:
        if term:
            pattern = f"%{term.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Sale.customer_name).like(pattern),
                    func.lower(Sale.customer_document_number).like(pattern),
                    func.lower(Sale.number).like(pattern),
                    func.lower(Sale.series + "-" + Sale.number).like(pattern),
                )
            )
        if document_type:
            stmt = stmt.where(Sale.document_type == document_type)
        if status:
            stmt = stmt.where(Sale.status == status)
        if patient_id is not None:
            stmt = stmt.where(Sale.patient_id == patient_id)
        if payment_method:
            stmt = stmt.where(Sale.payment_method == payment_method)
        if date_from is not None:
            stmt = stmt.where(Sale.issued_at >= start_of_day(date_from))
        if date_to is not None:
            stmt = stmt.where(Sale.issued_at <= end_of_day(date_to))
        return stmt


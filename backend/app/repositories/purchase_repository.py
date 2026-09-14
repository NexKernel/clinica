from datetime import date

from sqlalchemy import Select, func, or_, select

from app.models.purchase import Purchase, PurchaseStatus, Supplier
from app.repositories.base import BaseRepository
from app.schemas.common import Pagination


class SupplierRepository(BaseRepository[Supplier]):
    model = Supplier

    def tax_id_taken(self, tax_id: str, exclude_id: int | None = None) -> bool:
        stmt = select(Supplier.id).where(Supplier.tax_id == tax_id)
        if exclude_id is not None:
            stmt = stmt.where(Supplier.id != exclude_id)
        return self.db.execute(stmt).first() is not None

    def search(
        self,
        *,
        term: str | None = None,
        is_active: bool | None = None,
        pagination: Pagination,
    ) -> tuple[list[Supplier], int]:
        stmt = select(Supplier)
        if term:
            pattern = f"%{term.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Supplier.business_name).like(pattern),
                    func.lower(Supplier.trade_name).like(pattern),
                    func.lower(Supplier.tax_id).like(pattern),
                )
            )
        if is_active is not None:
            stmt = stmt.where(Supplier.is_active.is_(is_active))
        return self.paginate(stmt.order_by(Supplier.business_name), pagination)

    def list_active(self) -> list[Supplier]:
        stmt = (
            select(Supplier)
            .where(Supplier.is_active.is_(True))
            .order_by(Supplier.business_name)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_active(self) -> int:
        stmt = select(func.count(Supplier.id)).where(Supplier.is_active.is_(True))
        return self.db.execute(stmt).scalar_one()


class PurchaseRepository(BaseRepository[Purchase]):
    model = Purchase

    def document_taken(
        self,
        *,
        supplier_id: int,
        document_type: str,
        series: str | None,
        number: str | None,
        exclude_id: int | None = None,
    ) -> bool:
        if not number:
            return False
        series_match = Purchase.series.is_(None) if series is None else Purchase.series == series
        stmt = select(Purchase.id).where(
            Purchase.supplier_id == supplier_id,
            Purchase.document_type == document_type,
            series_match,
            Purchase.number == number,
        )
        if exclude_id is not None:
            stmt = stmt.where(Purchase.id != exclude_id)
        return self.db.execute(stmt).first() is not None

    def search(
        self,
        *,
        term: str | None = None,
        supplier_id: int | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        pagination: Pagination,
    ) -> tuple[list[Purchase], int]:
        stmt = self._apply_filters(
            select(Purchase).join(Purchase.supplier),
            term=term,
            supplier_id=supplier_id,
            status=status,
            date_from=date_from,
            date_to=date_to,
        ).order_by(Purchase.issue_date.desc(), Purchase.id.desc())
        return self.paginate(stmt, pagination)

    def count_by_status(self, status: str) -> int:
        stmt = select(func.count(Purchase.id)).where(Purchase.status == status)
        return self.db.execute(stmt).scalar_one()

    def totals_in_range(self, date_from: date, date_to: date) -> tuple[int, float]:
        stmt = select(func.count(Purchase.id), func.coalesce(func.sum(Purchase.total), 0)).where(
            Purchase.status == PurchaseStatus.RECIBIDA.value,
            Purchase.issue_date.between(date_from, date_to),
        )
        count, total = self.db.execute(stmt).one()
        return count, float(total)

    @staticmethod
    def _apply_filters(
        stmt: Select[tuple[Purchase]],
        *,
        term: str | None,
        supplier_id: int | None,
        status: str | None,
        date_from: date | None,
        date_to: date | None,
    ) -> Select[tuple[Purchase]]:
        if term:
            pattern = f"%{term.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Supplier.business_name).like(pattern),
                    func.lower(Purchase.number).like(pattern),
                )
            )
        if supplier_id is not None:
            stmt = stmt.where(Purchase.supplier_id == supplier_id)
        if status:
            stmt = stmt.where(Purchase.status == status)
        if date_from is not None:
            stmt = stmt.where(Purchase.issue_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(Purchase.issue_date <= date_to)
        return stmt

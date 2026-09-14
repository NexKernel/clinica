from datetime import date, timedelta

from sqlalchemy import Select, func, or_, select

from app.core.datetime import end_of_day, start_of_day
from app.core.datetime import today
from app.models.inventory import EXPIRY_ALERT_DAYS, Product, ProductCategory, StockMovement
from app.repositories.base import BaseRepository
from app.schemas.common import Pagination


class ProductCategoryRepository(BaseRepository[ProductCategory]):
    model = ProductCategory

    def list_all(self, *, only_active: bool = False) -> list[ProductCategory]:
        stmt = select(ProductCategory).order_by(ProductCategory.name)
        if only_active:
            stmt = stmt.where(ProductCategory.is_active.is_(True))
        return list(self.db.execute(stmt).scalars().all())

    def name_taken(self, name: str, exclude_id: int | None = None) -> bool:
        stmt = select(ProductCategory.id).where(
            func.lower(ProductCategory.name) == name.strip().lower()
        )
        if exclude_id is not None:
            stmt = stmt.where(ProductCategory.id != exclude_id)
        return self.db.execute(stmt).first() is not None


class ProductRepository(BaseRepository[Product]):
    model = Product

    def get_by_code(self, code: str) -> Product | None:
        stmt = select(Product).where(func.upper(Product.code) == code.strip().upper())
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def code_taken(self, code: str, exclude_id: int | None = None) -> bool:
        stmt = select(Product.id).where(func.upper(Product.code) == code.strip().upper())
        if exclude_id is not None:
            stmt = stmt.where(Product.id != exclude_id)
        return self.db.execute(stmt).first() is not None

    def next_code(self, prefix: str = "P") -> str:
        last = self.db.execute(select(func.max(Product.id))).scalar_one_or_none() or 0
        return f"{prefix}-{last + 1:05d}"

    def search(
        self,
        *,
        term: str | None = None,
        kind: str | None = None,
        category_id: int | None = None,
        is_active: bool | None = None,
        low_stock: bool = False,
        expiring: bool = False,
        pagination: Pagination,
    ) -> tuple[list[Product], int]:
        stmt = self._apply_filters(
            select(Product), term, kind, category_id, is_active, low_stock, expiring
        ).order_by(Product.name)
        return self.paginate(stmt, pagination)

    def quick_search(self, term: str, limit: int = 12) -> list[Product]:
        stmt = (
            self._apply_filters(select(Product), term, None, None, True, False, False)
            .order_by(Product.name)
            .limit(limit)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def list_low_stock(self, limit: int | None = None) -> list[Product]:
        """Productos en o por debajo del stock mínimo, los más críticos primero."""
        stmt = (
            select(Product)
            .where(
                Product.is_active.is_(True),
                Product.min_stock > 0,
                Product.stock <= Product.min_stock,
            )
            .order_by((Product.stock - Product.min_stock), Product.name)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.db.execute(stmt).unique().scalars().all())

    def list_expiring(self, *, days: int = EXPIRY_ALERT_DAYS, limit: int | None = None) -> list[Product]:
        """Productos con stock ya vencidos o próximos a vencer, los primeros arriba."""
        stmt = (
            select(Product)
            .where(
                Product.is_active.is_(True),
                Product.stock > 0,
                Product.expiry_date.is_not(None),
                Product.expiry_date <= today() + timedelta(days=days),
            )
            .order_by(Product.expiry_date, Product.name)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.db.execute(stmt).unique().scalars().all())

    def count_expiring(self, *, days: int = EXPIRY_ALERT_DAYS) -> int:
        stmt = select(func.count(Product.id)).where(
            Product.is_active.is_(True),
            Product.stock > 0,
            Product.expiry_date.is_not(None),
            Product.expiry_date <= today() + timedelta(days=days),
            Product.expiry_date >= today(),
        )
        return self.db.execute(stmt).scalar_one()

    def count_expired(self) -> int:
        stmt = select(func.count(Product.id)).where(
            Product.is_active.is_(True),
            Product.stock > 0,
            Product.expiry_date.is_not(None),
            Product.expiry_date < today(),
        )
        return self.db.execute(stmt).scalar_one()

    def count_all(self, *, is_active: bool | None = None) -> int:
        stmt = select(func.count(Product.id))
        if is_active is not None:
            stmt = stmt.where(Product.is_active.is_(is_active))
        return self.db.execute(stmt).scalar_one()

    def count_low_stock(self) -> int:
        stmt = select(func.count(Product.id)).where(
            Product.is_active.is_(True),
            Product.min_stock > 0,
            Product.stock <= Product.min_stock,
        )
        return self.db.execute(stmt).scalar_one()

    def count_out_of_stock(self) -> int:
        stmt = select(func.count(Product.id)).where(
            Product.is_active.is_(True), Product.stock <= 0
        )
        return self.db.execute(stmt).scalar_one()

    def inventory_value(self) -> float:
        stmt = select(func.coalesce(func.sum(Product.stock * Product.purchase_price), 0)).where(
            Product.is_active.is_(True)
        )
        return float(self.db.execute(stmt).scalar_one())

    @staticmethod
    def _apply_filters(
        stmt: Select[tuple[Product]],
        term: str | None,
        kind: str | None,
        category_id: int | None,
        is_active: bool | None,
        low_stock: bool,
        expiring: bool,
    ) -> Select[tuple[Product]]:
        if term:
            pattern = f"%{term.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(Product.name).like(pattern),
                    func.lower(Product.code).like(pattern),
                    func.lower(Product.barcode).like(pattern),
                    func.lower(Product.laboratory).like(pattern),
                )
            )
        if kind:
            stmt = stmt.where(Product.kind == kind)
        if category_id is not None:
            stmt = stmt.where(Product.category_id == category_id)
        if is_active is not None:
            stmt = stmt.where(Product.is_active.is_(is_active))
        if low_stock:
            stmt = stmt.where(Product.min_stock > 0, Product.stock <= Product.min_stock)
        if expiring:
            stmt = stmt.where(
                Product.stock > 0,
                Product.expiry_date.is_not(None),
                Product.expiry_date <= today() + timedelta(days=EXPIRY_ALERT_DAYS),
            )
        return stmt


class StockMovementRepository(BaseRepository[StockMovement]):
    model = StockMovement

    def search(
        self,
        *,
        product_id: int | None = None,
        movement_type: str | None = None,
        reason: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        pagination: Pagination,
    ) -> tuple[list[StockMovement], int]:
        stmt = select(StockMovement)
        if product_id is not None:
            stmt = stmt.where(StockMovement.product_id == product_id)
        if movement_type:
            stmt = stmt.where(StockMovement.movement_type == movement_type)
        if reason:
            stmt = stmt.where(StockMovement.reason == reason)
        if date_from is not None:
            stmt = stmt.where(StockMovement.occurred_at >= start_of_day(date_from))
        if date_to is not None:
            stmt = stmt.where(StockMovement.occurred_at <= end_of_day(date_to))
        stmt = stmt.order_by(StockMovement.occurred_at.desc(), StockMovement.id.desc())
        return self.paginate(stmt, pagination)

    def list_for_reference(self, reference_type: str, reference_id: int) -> list[StockMovement]:
        stmt = select(StockMovement).where(
            StockMovement.reference_type == reference_type,
            StockMovement.reference_id == reference_id,
        )
        return list(self.db.execute(stmt).unique().scalars().all())

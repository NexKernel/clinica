from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.datetime import now, to_local
from app.models.inventory import (
    MovementReason,
    MovementType,
    Product,
    ProductCategory,
    StockMovement,
)
from app.models.user import User
from app.repositories.inventory_repository import (
    ProductCategoryRepository,
    ProductRepository,
    StockMovementRepository,
)
from app.schemas.common import Pagination
from app.schemas.inventory import (
    CategoryCreate,
    CategoryUpdate,
    InventoryStats,
    MovementCreate,
    ProductCreate,
    ProductUpdate,
    StockAdjustment,
)
from app.services.exceptions import BusinessRuleError, ConflictError, NotFoundError

# Motivos que corresponden a cada tipo de movimiento.
ENTRY_REASONS = {
    MovementReason.COMPRA.value,
    MovementReason.DEVOLUCION.value,
    MovementReason.INVENTARIO_INICIAL.value,
    MovementReason.ANULACION.value,
}
EXIT_REASONS = {
    MovementReason.VENTA.value,
    MovementReason.DISPENSACION.value,
    MovementReason.MERMA.value,
    MovementReason.VENCIMIENTO.value,
}


class InventoryService:
    """Farmacia y almacén: catálogo, existencias y kardex (cláusula 2.6)."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.products = ProductRepository(db)
        self.categories = ProductCategoryRepository(db)
        self.movements = StockMovementRepository(db)

    # --- Categorías -----------------------------------------------------
    def list_categories(self, *, only_active: bool = False) -> list[ProductCategory]:
        return self.categories.list_all(only_active=only_active)

    def create_category(self, payload: CategoryCreate) -> ProductCategory:
        if self.categories.name_taken(payload.name):
            raise ConflictError("Ya existe una categoría con ese nombre")
        return self.categories.add(ProductCategory(**payload.model_dump()))

    def update_category(self, category_id: int, payload: CategoryUpdate) -> ProductCategory:
        category = self.categories.get_by_id(category_id)
        if category is None:
            raise NotFoundError("La categoría no existe")
        if self.categories.name_taken(payload.name, exclude_id=category.id):
            raise ConflictError("Ya existe una categoría con ese nombre")
        for field, value in payload.model_dump().items():
            setattr(category, field, value)
        return self.categories.save(category)

    # --- Productos ------------------------------------------------------
    def list_products(self, **filters) -> tuple[list[Product], int]:
        pagination: Pagination = filters.pop("pagination")
        return self.products.search(pagination=pagination, **filters)

    def quick_search(self, term: str) -> list[Product]:
        if not term or len(term.strip()) < 2:
            return []
        return self.products.quick_search(term)

    def get_product(self, product_id: int) -> Product:
        product = self.products.get_by_id(product_id)
        if product is None:
            raise NotFoundError("El producto no existe")
        return product

    def create_product(self, payload: ProductCreate, actor: User) -> Product:
        self._validate_stock_limits(payload.min_stock, payload.max_stock)
        self._validate_category(payload.category_id)

        code = (payload.code or self.products.next_code()).strip().upper()
        if self.products.code_taken(code):
            raise ConflictError("Ya existe un producto con ese código")

        data = payload.model_dump(exclude={"code", "initial_stock"})
        data["kind"] = payload.kind.value
        product = self.products.add(Product(code=code, stock=0, **data))

        if payload.initial_stock > 0:
            self.apply_movement(
                product=product,
                movement_type=MovementType.ENTRADA,
                reason=MovementReason.INVENTARIO_INICIAL,
                quantity=payload.initial_stock,
                unit_cost=payload.purchase_price,
                actor=actor,
                notes="Carga inicial de inventario",
            )
        return product

    def update_product(self, product_id: int, payload: ProductUpdate) -> Product:
        product = self.get_product(product_id)
        self._validate_stock_limits(payload.min_stock, payload.max_stock)
        self._validate_category(payload.category_id)
        if self.products.code_taken(payload.code, exclude_id=product.id):
            raise ConflictError("Ya existe un producto con ese código")

        data = payload.model_dump()
        data["kind"] = payload.kind.value
        data["code"] = payload.code.strip().upper()
        for field, value in data.items():
            setattr(product, field, value)
        return self.products.save(product)

    def set_product_active(self, product_id: int, is_active: bool) -> Product:
        product = self.get_product(product_id)
        product.is_active = is_active
        return self.products.save(product)

    # --- Movimientos ----------------------------------------------------
    def list_movements(self, **filters) -> tuple[list[StockMovement], int]:
        pagination: Pagination = filters.pop("pagination")
        return self.movements.search(pagination=pagination, **filters)

    def register_movement(self, payload: MovementCreate, actor: User) -> StockMovement:
        product = self.get_product(payload.product_id)
        self._validate_reason(payload.movement_type, payload.reason)
        return self.apply_movement(
            product=product,
            movement_type=payload.movement_type,
            reason=payload.reason,
            quantity=payload.quantity,
            unit_cost=payload.unit_cost,
            lot=payload.lot,
            expiry_date=payload.expiry_date,
            occurred_at=payload.occurred_at,
            notes=payload.notes,
            actor=actor,
        )

    def adjust_stock(self, payload: StockAdjustment, actor: User) -> StockMovement:
        """Cuadra el stock del sistema con el conteo físico."""
        product = self.get_product(payload.product_id)
        difference = payload.counted_stock - product.stock
        if difference == 0:
            raise BusinessRuleError("El stock del sistema ya coincide con el conteo")

        return self.apply_movement(
            product=product,
            movement_type=MovementType.AJUSTE,
            reason=MovementReason.AJUSTE_MANUAL,
            quantity=abs(difference),
            target_stock=payload.counted_stock,
            notes=payload.notes or "Ajuste por inventario físico",
            actor=actor,
        )

    def apply_movement(
        self,
        *,
        product: Product,
        movement_type: MovementType,
        reason: MovementReason,
        quantity: int,
        unit_cost: Decimal | None = None,
        lot: str | None = None,
        expiry_date: date | None = None,
        occurred_at: datetime | None = None,
        notes: str | None = None,
        reference_type: str | None = None,
        reference_id: int | None = None,
        target_stock: int | None = None,
        actor: User | None = None,
        commit: bool = True,
    ) -> StockMovement:
        """Aplica el movimiento y deja el producto con su nuevo stock.

        Con `commit=False` la operación queda pendiente en la transacción, para
        que compras y ventas registren todos sus movimientos de una sola vez.
        """
        stock_before = product.stock
        if target_stock is not None:
            stock_after = target_stock
        elif movement_type is MovementType.ENTRADA:
            stock_after = stock_before + quantity
        else:
            stock_after = stock_before - quantity
            if stock_after < 0:
                raise BusinessRuleError(
                    f"Stock insuficiente de {product.full_name}: "
                    f"disponible {stock_before}, solicitado {quantity}"
                )

        movement = StockMovement(
            product_id=product.id,
            movement_type=movement_type.value,
            reason=reason.value,
            quantity=quantity,
            stock_before=stock_before,
            stock_after=stock_after,
            unit_cost=unit_cost,
            lot=lot,
            expiry_date=expiry_date,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            occurred_at=to_local(occurred_at) if occurred_at else now(),
            created_by_id=actor.id if actor else None,
        )
        product.stock = stock_after
        if movement_type is MovementType.ENTRADA:
            if unit_cost is not None:
                product.purchase_price = unit_cost
            # Se dispensa primero lo que vence antes: el producto refleja el
            # lote más próximo a caducar de los que tiene en existencia.
            if expiry_date is not None and (
                product.expiry_date is None or expiry_date < product.expiry_date
            ):
                product.expiry_date = expiry_date
                product.lot = lot

        self.db.add_all([movement, product])
        if commit:
            self.db.commit()
            self.db.refresh(movement)
        else:
            self.db.flush()
        return movement

    # --- Indicadores ----------------------------------------------------
    def stats(self) -> InventoryStats:
        return InventoryStats(
            total_products=self.products.count_all(),
            active_products=self.products.count_all(is_active=True),
            low_stock=self.products.count_low_stock(),
            out_of_stock=self.products.count_out_of_stock(),
            expiring_soon=self.products.count_expiring(),
            expired=self.products.count_expired(),
            inventory_value=round(self.products.inventory_value(), 2),
        )

    def low_stock(self, limit: int | None = None) -> list[Product]:
        return self.products.list_low_stock(limit)

    def expiring(self, limit: int | None = None) -> list[Product]:
        return self.products.list_expiring(limit=limit)

    # --- Apoyo ----------------------------------------------------------
    @staticmethod
    def _validate_stock_limits(min_stock: int, max_stock: int) -> None:
        if max_stock and max_stock < min_stock:
            raise BusinessRuleError("El stock máximo debe ser mayor o igual al mínimo")

    def _validate_category(self, category_id: int | None) -> None:
        if category_id is not None and self.categories.get_by_id(category_id) is None:
            raise BusinessRuleError("La categoría indicada no existe")

    @staticmethod
    def _validate_reason(movement_type: MovementType, reason: MovementReason) -> None:
        if movement_type is MovementType.ENTRADA and reason.value not in ENTRY_REASONS:
            raise BusinessRuleError("El motivo indicado no corresponde a una entrada")
        if movement_type is MovementType.SALIDA and reason.value not in EXIT_REASONS:
            raise BusinessRuleError("El motivo indicado no corresponde a una salida")
        if movement_type is MovementType.AJUSTE and reason is not MovementReason.AJUSTE_MANUAL:
            raise BusinessRuleError("Los ajustes se registran con el motivo de ajuste manual")

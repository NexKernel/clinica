from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.datetime import now, today
from app.models.inventory import MovementReason, MovementType
from app.models.purchase import Purchase, PurchaseItem, PurchaseStatus, Supplier
from app.models.user import User
from app.repositories.inventory_repository import ProductRepository
from app.repositories.purchase_repository import PurchaseRepository, SupplierRepository
from app.schemas.common import Pagination
from app.schemas.purchase import (
    PurchaseCreate,
    PurchaseStats,
    PurchaseUpdate,
    SupplierCreate,
    SupplierUpdate,
)
from app.services.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.services.inventory_service import InventoryService
from app.services.settings_service import SettingsService

REFERENCE_TYPE = "PURCHASE"
CENTS = Decimal("0.01")


class PurchaseService:
    """Proveedores, compras e ingreso al inventario (cláusula 2.7)."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.purchases = PurchaseRepository(db)
        self.suppliers = SupplierRepository(db)
        self.products = ProductRepository(db)
        self.inventory = InventoryService(db)

    # --- Proveedores ----------------------------------------------------
    def list_suppliers(
        self, *, term: str | None, is_active: bool | None, pagination: Pagination
    ) -> tuple[list[Supplier], int]:
        return self.suppliers.search(term=term, is_active=is_active, pagination=pagination)

    def list_active_suppliers(self) -> list[Supplier]:
        return self.suppliers.list_active()

    def get_supplier(self, supplier_id: int) -> Supplier:
        supplier = self.suppliers.get_by_id(supplier_id)
        if supplier is None:
            raise NotFoundError("El proveedor no existe")
        return supplier

    def create_supplier(self, payload: SupplierCreate) -> Supplier:
        self._ensure_tax_id_available(payload.tax_id)
        return self.suppliers.add(Supplier(**self._supplier_fields(payload)))

    def update_supplier(self, supplier_id: int, payload: SupplierUpdate) -> Supplier:
        supplier = self.get_supplier(supplier_id)
        self._ensure_tax_id_available(payload.tax_id, exclude_id=supplier.id)
        for field, value in self._supplier_fields(payload).items():
            setattr(supplier, field, value)
        return self.suppliers.save(supplier)

    # --- Compras --------------------------------------------------------
    def list_purchases(self, **filters) -> tuple[list[Purchase], int]:
        pagination: Pagination = filters.pop("pagination")
        return self.purchases.search(pagination=pagination, **filters)

    def get(self, purchase_id: int) -> Purchase:
        purchase = self.purchases.get_by_id(purchase_id)
        if purchase is None:
            raise NotFoundError("La compra no existe")
        return purchase

    def create(self, payload: PurchaseCreate, actor: User) -> Purchase:
        supplier = self.get_supplier(payload.supplier_id)
        self._ensure_document_available(payload, supplier.id)

        purchase = Purchase(
            supplier_id=supplier.id,
            document_type=payload.document_type.value,
            series=payload.series,
            number=payload.number,
            issue_date=payload.issue_date,
            status=PurchaseStatus.BORRADOR.value,
            notes=payload.notes,
            created_by_id=actor.id,
        )
        purchase.items = self._build_items(payload)
        self._apply_totals(purchase, payload.apply_tax)
        return self.purchases.add(purchase)

    def update(self, purchase_id: int, payload: PurchaseUpdate) -> Purchase:
        purchase = self.get(purchase_id)
        if not purchase.is_editable:
            raise BusinessRuleError("Solo se pueden modificar compras en borrador")

        supplier = self.get_supplier(payload.supplier_id)
        self._ensure_document_available(payload, supplier.id, exclude_id=purchase.id)

        purchase.supplier_id = supplier.id
        purchase.document_type = payload.document_type.value
        purchase.series = payload.series
        purchase.number = payload.number
        purchase.issue_date = payload.issue_date
        purchase.notes = payload.notes
        purchase.items = self._build_items(payload)
        self._apply_totals(purchase, payload.apply_tax)
        return self.purchases.save(purchase)

    def receive(self, purchase_id: int, actor: User) -> Purchase:
        """Ingresa los productos al inventario y cierra la compra."""
        purchase = self.get(purchase_id)
        if purchase.status == PurchaseStatus.RECIBIDA.value:
            raise BusinessRuleError("La compra ya fue ingresada al inventario")
        if purchase.status == PurchaseStatus.ANULADA.value:
            raise BusinessRuleError("La compra está anulada")
        if not purchase.items:
            raise BusinessRuleError("La compra no tiene productos")

        for item in purchase.items:
            self.inventory.apply_movement(
                product=item.product,
                movement_type=MovementType.ENTRADA,
                reason=MovementReason.COMPRA,
                quantity=item.quantity,
                unit_cost=item.unit_cost,
                lot=item.lot,
                expiry_date=item.expiry_date,
                reference_type=REFERENCE_TYPE,
                reference_id=purchase.id,
                notes=f"Compra {purchase.document_number or purchase.id}",
                actor=actor,
                commit=False,
            )

        purchase.status = PurchaseStatus.RECIBIDA.value
        purchase.received_at = now()
        return self.purchases.save(purchase)

    def cancel(self, purchase_id: int, reason: str, actor: User) -> Purchase:
        """Anula la compra y revierte el ingreso al inventario si corresponde."""
        purchase = self.get(purchase_id)
        if purchase.status == PurchaseStatus.ANULADA.value:
            return purchase

        if purchase.status == PurchaseStatus.RECIBIDA.value:
            for item in purchase.items:
                self.inventory.apply_movement(
                    product=item.product,
                    movement_type=MovementType.SALIDA,
                    reason=MovementReason.DEVOLUCION,
                    quantity=item.quantity,
                    reference_type=REFERENCE_TYPE,
                    reference_id=purchase.id,
                    notes=f"Anulación de compra {purchase.document_number or purchase.id}",
                    actor=actor,
                    commit=False,
                )

        purchase.status = PurchaseStatus.ANULADA.value
        purchase.cancel_reason = reason
        return self.purchases.save(purchase)

    # --- Indicadores ----------------------------------------------------
    def stats(self) -> PurchaseStats:
        reference = today()
        first_day = reference.replace(day=1)
        count, amount = self.purchases.totals_in_range(first_day, reference)
        return PurchaseStats(
            drafts=self.purchases.count_by_status(PurchaseStatus.BORRADOR.value),
            received_this_month=count,
            amount_this_month=round(amount, 2),
            active_suppliers=self.suppliers.count_active(),
        )

    # --- Apoyo ----------------------------------------------------------
    def _build_items(self, payload: PurchaseCreate) -> list[PurchaseItem]:
        items: list[PurchaseItem] = []
        seen: set[int] = set()
        for entry in payload.items:
            product = self.products.get_by_id(entry.product_id)
            if product is None:
                raise BusinessRuleError("Uno de los productos indicados no existe")
            if product.id in seen:
                raise BusinessRuleError(f"El producto {product.name} está repetido en el detalle")
            seen.add(product.id)

            if entry.expiry_date is not None and entry.expiry_date < today():
                raise BusinessRuleError(
                    f"El lote de {product.name} ya está vencido: revise la fecha"
                )

            items.append(
                PurchaseItem(
                    product_id=product.id,
                    quantity=entry.quantity,
                    unit_cost=entry.unit_cost,
                    subtotal=(entry.unit_cost * entry.quantity).quantize(CENTS),
                    lot=entry.lot,
                    expiry_date=entry.expiry_date,
                )
            )
        return items

    def _apply_totals(self, purchase: Purchase, apply_tax: bool) -> None:
        subtotal = sum((item.subtotal for item in purchase.items), Decimal("0.00"))
        rate = Decimal(str(SettingsService(self.db).get().tax_rate)) if apply_tax else Decimal("0")
        tax = (subtotal * rate / Decimal("100")).quantize(CENTS)
        purchase.subtotal = subtotal.quantize(CENTS)
        purchase.tax = tax
        purchase.total = (subtotal + tax).quantize(CENTS)

    def _ensure_tax_id_available(self, tax_id: str | None, exclude_id: int | None = None) -> None:
        if tax_id and self.suppliers.tax_id_taken(tax_id, exclude_id=exclude_id):
            raise ConflictError("Ya existe un proveedor registrado con ese RUC")

    def _ensure_document_available(
        self, payload: PurchaseCreate, supplier_id: int, exclude_id: int | None = None
    ) -> None:
        if payload.issue_date > today():
            raise BusinessRuleError("La fecha del documento no puede ser futura")
        if self.purchases.document_taken(
            supplier_id=supplier_id,
            document_type=payload.document_type.value,
            series=payload.series,
            number=payload.number,
            exclude_id=exclude_id,
        ):
            raise ConflictError("Ese documento ya está registrado para el proveedor")

    @staticmethod
    def _supplier_fields(payload: SupplierCreate | SupplierUpdate) -> dict[str, object]:
        data = payload.model_dump()
        data["email"] = str(payload.email) if payload.email else None
        return data

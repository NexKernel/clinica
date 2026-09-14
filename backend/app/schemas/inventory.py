from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.inventory import MovementReason, MovementType, ProductKind
from app.schemas.types import LocalDatetime


class _CleanStrings(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = " ".join(value.split())
            return cleaned or None
        return value


class CategoryBase(_CleanStrings):
    name: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    is_active: bool = True


class CategoryCreate(CategoryBase):
    """Alta de categoría de productos."""


class CategoryUpdate(CategoryBase):
    """Actualización de categoría."""


class CategoryRead(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class ProductBase(_CleanStrings):
    name: str = Field(min_length=2, max_length=160)
    kind: ProductKind = ProductKind.MEDICAMENTO
    category_id: int | None = None
    barcode: str | None = Field(default=None, max_length=40)
    presentation: str | None = Field(default=None, max_length=80)
    concentration: str | None = Field(default=None, max_length=60)
    unit: str = Field(default="UNIDAD", min_length=1, max_length=20)
    laboratory: str | None = Field(default=None, max_length=120)
    requires_prescription: bool = False

    purchase_price: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=10, decimal_places=2)
    sale_price: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=10, decimal_places=2)

    min_stock: int = Field(default=0, ge=0, le=1_000_000)
    max_stock: int = Field(default=0, ge=0, le=1_000_000)
    location: str | None = Field(default=None, max_length=60)
    lot: str | None = Field(default=None, max_length=40)
    expiry_date: date | None = Field(
        default=None, description="Vencimiento del lote en existencia"
    )
    notes: str | None = Field(default=None, max_length=1000)
    is_active: bool = True


class ProductCreate(ProductBase):
    """Alta de producto. El código se genera si no se indica."""

    code: str | None = Field(default=None, max_length=24)
    initial_stock: int = Field(default=0, ge=0, le=1_000_000)


class ProductUpdate(ProductBase):
    """Actualización del producto. El stock se ajusta con movimientos."""

    code: str = Field(min_length=2, max_length=24)


class ProductRead(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    full_name: str
    category_name: str | None
    kind_label: str
    stock: int
    needs_restock: bool
    is_out_of_stock: bool
    suggested_purchase: int
    days_to_expiry: int | None
    is_expired: bool
    expires_soon: bool
    expiry_label: str | None
    updated_at: LocalDatetime


class ProductSummary(BaseModel):
    """Producto en selectores de recetas, ventas y compras."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    full_name: str
    unit: str
    stock: int
    sale_price: Decimal
    purchase_price: Decimal
    requires_prescription: bool
    needs_restock: bool
    expiry_date: date | None
    is_expired: bool
    expires_soon: bool


class MovementCreate(BaseModel):
    """Entrada, salida o ajuste registrado desde el módulo de almacén."""

    product_id: int
    movement_type: MovementType
    reason: MovementReason
    quantity: int = Field(gt=0, le=1_000_000)
    unit_cost: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    lot: str | None = Field(default=None, max_length=40)
    expiry_date: date | None = None
    occurred_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=255)


class StockAdjustment(BaseModel):
    """Corrección del stock tras un inventario físico."""

    product_id: int
    counted_stock: int = Field(ge=0, le=1_000_000)
    notes: str | None = Field(default=None, max_length=255)


class MovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    product_name: str
    movement_type: str
    reason: str
    reason_label: str
    quantity: int
    signed_quantity: int
    stock_before: int
    stock_after: int
    unit_cost: Decimal | None
    lot: str | None
    expiry_date: date | None
    reference_type: str | None
    reference_id: int | None
    notes: str | None
    occurred_at: LocalDatetime


class InventoryStats(BaseModel):
    """Indicadores de farmacia y almacén."""

    total_products: int
    active_products: int
    low_stock: int
    out_of_stock: int
    expiring_soon: int
    expired: int
    inventory_value: float


class ExpiringItem(BaseModel):
    """Producto con stock vencido o próximo a vencer."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    full_name: str
    unit: str
    stock: int
    lot: str | None
    expiry_date: date | None
    days_to_expiry: int | None
    expiry_label: str | None
    is_expired: bool
    category_name: str | None


class LowStockItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    full_name: str
    unit: str
    stock: int
    min_stock: int
    max_stock: int
    suggested_purchase: int
    is_out_of_stock: bool
    category_name: str | None

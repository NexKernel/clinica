from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.datetime import today
from app.db.base import Base, TimestampMixin


class ProductKind(StrEnum):
    MEDICAMENTO = "MEDICAMENTO"
    INSUMO = "INSUMO"
    ORTOPEDICO = "ORTOPEDICO"
    UNIFORME = "UNIFORME"
    OPTICA = "OPTICA"
    OTRO = "OTRO"


PRODUCT_KIND_LABELS: dict[str, str] = {
    ProductKind.MEDICAMENTO.value: "Medicamento",
    ProductKind.INSUMO.value: "Insumo médico",
    ProductKind.ORTOPEDICO.value: "Producto ortopédico",
    ProductKind.UNIFORME.value: "Uniforme de enfermería",
    ProductKind.OPTICA.value: "Óptica",
    ProductKind.OTRO.value: "Otro",
}


class MovementType(StrEnum):
    ENTRADA = "ENTRADA"
    SALIDA = "SALIDA"
    AJUSTE = "AJUSTE"


class MovementReason(StrEnum):
    COMPRA = "COMPRA"
    VENTA = "VENTA"
    DISPENSACION = "DISPENSACION"
    DEVOLUCION = "DEVOLUCION"
    MERMA = "MERMA"
    VENCIMIENTO = "VENCIMIENTO"
    INVENTARIO_INICIAL = "INVENTARIO_INICIAL"
    AJUSTE_MANUAL = "AJUSTE_MANUAL"
    ANULACION = "ANULACION"


MOVEMENT_REASON_LABELS: dict[str, str] = {
    MovementReason.COMPRA.value: "Ingreso por compra",
    MovementReason.VENTA.value: "Salida por venta",
    MovementReason.DISPENSACION.value: "Dispensación al paciente",
    MovementReason.DEVOLUCION.value: "Devolución",
    MovementReason.MERMA.value: "Merma o pérdida",
    MovementReason.VENCIMIENTO.value: "Producto vencido",
    MovementReason.INVENTARIO_INICIAL.value: "Inventario inicial",
    MovementReason.AJUSTE_MANUAL.value: "Ajuste manual",
    MovementReason.ANULACION.value: "Reposición por anulación",
}


# Días de antelación con que se avisa el vencimiento de un producto.
EXPIRY_ALERT_DAYS = 60


class ProductCategory(Base, TimestampMixin):
    """Agrupación de productos de farmacia y almacén."""

    __tablename__ = "product_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Base, TimestampMixin):
    """Medicamento, insumo o producto comercializado por el policlínico."""

    __tablename__ = "products"
    __table_args__ = (Index("ix_products_name", "name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(24), unique=True, index=True, nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default=ProductKind.MEDICAMENTO.value, nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("product_categories.id"))

    presentation: Mapped[str | None] = mapped_column(String(80))
    concentration: Mapped[str | None] = mapped_column(String(60))
    unit: Mapped[str] = mapped_column(String(20), default="UNIDAD", nullable=False)
    laboratory: Mapped[str | None] = mapped_column(String(120))
    requires_prescription: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    purchase_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    sale_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    min_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    location: Mapped[str | None] = mapped_column(String(60))

    # Vencimiento del lote en existencia. El detalle por lote queda en el
    # kardex y en cada compra; aquí se refleja el más próximo a vencer, que
    # es el que el personal debe dispensar primero.
    lot: Mapped[str | None] = mapped_column(String(40))
    expiry_date: Mapped[date | None] = mapped_column(Date, index=True)

    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped[ProductCategory | None] = relationship(back_populates="products", lazy="joined")

    @property
    def category_name(self) -> str | None:
        return self.category.name if self.category else None

    @property
    def kind_label(self) -> str:
        return PRODUCT_KIND_LABELS.get(self.kind, self.kind)

    @property
    def full_name(self) -> str:
        parts = [self.name, self.concentration, self.presentation]
        return " ".join(part for part in parts if part)

    @property
    def needs_restock(self) -> bool:
        """Producto en o por debajo del stock mínimo configurado."""
        return self.min_stock > 0 and self.stock <= self.min_stock

    @property
    def is_out_of_stock(self) -> bool:
        return self.stock <= 0

    @property
    def days_to_expiry(self) -> int | None:
        """Días que faltan para el vencimiento; negativo si ya venció."""
        if self.expiry_date is None:
            return None
        return (self.expiry_date - today()).days

    @property
    def is_expired(self) -> bool:
        days = self.days_to_expiry
        return days is not None and days < 0

    @property
    def expires_soon(self) -> bool:
        """Producto con stock cuyo vencimiento entra en la ventana de aviso."""
        days = self.days_to_expiry
        return days is not None and 0 <= days <= EXPIRY_ALERT_DAYS and self.stock > 0

    @property
    def expiry_label(self) -> str | None:
        days = self.days_to_expiry
        if days is None:
            return None
        if days < 0:
            return f"Vencido hace {abs(days)} día{'s' if abs(days) != 1 else ''}"
        if days == 0:
            return "Vence hoy"
        return f"Vence en {days} día{'s' if days != 1 else ''}"

    @property
    def suggested_purchase(self) -> int:
        """Unidades sugeridas para volver al stock máximo."""
        if self.max_stock <= 0 or self.stock >= self.max_stock:
            return 0
        return self.max_stock - self.stock


class StockMovement(Base, TimestampMixin):
    """Kardex: toda entrada, salida o ajuste deja registro (cláusula 2.6)."""

    __tablename__ = "stock_movements"
    __table_args__ = (Index("ix_stock_movements_product_date", "product_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    movement_type: Mapped[str] = mapped_column(String(12), nullable=False)
    reason: Mapped[str] = mapped_column(String(24), nullable=False)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_before: Mapped[int] = mapped_column(Integer, nullable=False)
    stock_after: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))

    lot: Mapped[str | None] = mapped_column(String(40))
    expiry_date: Mapped[date | None] = mapped_column(Date)

    reference_type: Mapped[str | None] = mapped_column(String(24))
    reference_id: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(String(255))

    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    product: Mapped[Product] = relationship(lazy="joined")

    @property
    def product_name(self) -> str:
        return self.product.full_name

    @property
    def reason_label(self) -> str:
        return MOVEMENT_REASON_LABELS.get(self.reason, self.reason)

    @property
    def signed_quantity(self) -> int:
        return self.stock_after - self.stock_before

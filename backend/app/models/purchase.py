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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.inventory import Product

ZERO = Decimal("0.00")


class SupplierDocumentType(StrEnum):
    FACTURA = "FACTURA"
    BOLETA = "BOLETA"
    GUIA_REMISION = "GUIA_REMISION"
    OTRO = "OTRO"


SUPPLIER_DOCUMENT_LABELS: dict[str, str] = {
    SupplierDocumentType.FACTURA.value: "Factura",
    SupplierDocumentType.BOLETA.value: "Boleta",
    SupplierDocumentType.GUIA_REMISION.value: "Guía de remisión",
    SupplierDocumentType.OTRO.value: "Otro documento",
}


class PurchaseStatus(StrEnum):
    BORRADOR = "BORRADOR"
    RECIBIDA = "RECIBIDA"
    ANULADA = "ANULADA"


PURCHASE_STATUS_LABELS: dict[str, str] = {
    PurchaseStatus.BORRADOR.value: "Borrador",
    PurchaseStatus.RECIBIDA.value: "Recibida",
    PurchaseStatus.ANULADA.value: "Anulada",
}


class Supplier(Base, TimestampMixin):
    """Proveedor de medicamentos, insumos y productos (cláusula 2.7)."""

    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    tax_id: Mapped[str | None] = mapped_column(String(11), unique=True, index=True)
    business_name: Mapped[str] = mapped_column(String(180), nullable=False, index=True)
    trade_name: Mapped[str | None] = mapped_column(String(180))
    contact_name: Mapped[str | None] = mapped_column(String(160))
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(160))
    address: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def display_name(self) -> str:
        return self.trade_name or self.business_name


class Purchase(Base, TimestampMixin):
    """Compra registrada e ingresada al inventario (cláusula 2.7)."""

    __tablename__ = "purchases"
    __table_args__ = (
        UniqueConstraint(
            "supplier_id", "document_type", "series", "number", name="uq_purchase_document"
        ),
        Index("ix_purchases_date", "issue_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), nullable=False)

    document_type: Mapped[str] = mapped_column(
        String(20), default=SupplierDocumentType.FACTURA.value, nullable=False
    )
    series: Mapped[str | None] = mapped_column(String(10))
    number: Mapped[str | None] = mapped_column(String(20))
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    status: Mapped[str] = mapped_column(
        String(12), default=PurchaseStatus.BORRADOR.value, nullable=False, index=True
    )
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=ZERO, nullable=False)
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=ZERO, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=ZERO, nullable=False)

    notes: Mapped[str | None] = mapped_column(Text)
    cancel_reason: Mapped[str | None] = mapped_column(String(255))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    supplier: Mapped[Supplier] = relationship(lazy="joined")
    items: Mapped[list["PurchaseItem"]] = relationship(
        back_populates="purchase",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="PurchaseItem.id",
    )

    @property
    def status_label(self) -> str:
        return PURCHASE_STATUS_LABELS.get(self.status, self.status)

    @property
    def document_label(self) -> str:
        return SUPPLIER_DOCUMENT_LABELS.get(self.document_type, self.document_type)

    @property
    def document_number(self) -> str | None:
        if self.series and self.number:
            return f"{self.series}-{self.number}"
        return self.number or None

    @property
    def supplier_name(self) -> str:
        return self.supplier.display_name

    @property
    def item_count(self) -> int:
        return len(self.items)

    @property
    def total_units(self) -> int:
        return sum(item.quantity for item in self.items)

    @property
    def is_editable(self) -> bool:
        return self.status == PurchaseStatus.BORRADOR.value


class PurchaseItem(Base, TimestampMixin):
    """Detalle de la compra: producto, cantidad y costo unitario."""

    __tablename__ = "purchase_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_id: Mapped[int] = mapped_column(
        ForeignKey("purchases.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=ZERO, nullable=False)
    lot: Mapped[str | None] = mapped_column(String(40))
    expiry_date: Mapped[date | None] = mapped_column(Date)

    purchase: Mapped[Purchase] = relationship(back_populates="items")
    product: Mapped[Product] = relationship(lazy="joined")

    @property
    def product_name(self) -> str:
        return self.product.full_name

    @property
    def product_code(self) -> str:
        return self.product.code

    @property
    def unit(self) -> str:
        return self.product.unit

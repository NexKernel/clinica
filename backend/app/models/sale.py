from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    Boolean,
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

from app.models.catalog import MedicalService
from app.models.inventory import Product
from app.models.patient import Patient
from app.db.base import Base, TimestampMixin

ZERO = Decimal("0.00")


class DocumentType(StrEnum):
    NOTA_VENTA = "NOTA_VENTA"
    BOLETA = "BOLETA"
    FACTURA = "FACTURA"


DOCUMENT_TYPE_LABELS: dict[str, str] = {
    DocumentType.NOTA_VENTA.value: "Nota de venta",
    DocumentType.BOLETA.value: "Boleta de venta",
    DocumentType.FACTURA.value: "Factura",
}

# Documentos electrónicos: exigen datos completos del cliente (cláusula 2.9).
ELECTRONIC_DOCUMENTS: tuple[str, ...] = (
    DocumentType.BOLETA.value,
    DocumentType.FACTURA.value,
)


class PaymentMethod(StrEnum):
    EFECTIVO = "EFECTIVO"
    TARJETA = "TARJETA"
    YAPE = "YAPE"
    PLIN = "PLIN"
    TRANSFERENCIA = "TRANSFERENCIA"
    CREDITO = "CREDITO"


PAYMENT_METHOD_LABELS: dict[str, str] = {
    PaymentMethod.EFECTIVO.value: "Efectivo",
    PaymentMethod.TARJETA.value: "Tarjeta",
    PaymentMethod.YAPE.value: "Yape",
    PaymentMethod.PLIN.value: "Plin",
    PaymentMethod.TRANSFERENCIA.value: "Transferencia",
    PaymentMethod.CREDITO.value: "Crédito",
}


class SaleStatus(StrEnum):
    EMITIDA = "EMITIDA"
    ANULADA = "ANULADA"


SALE_STATUS_LABELS: dict[str, str] = {
    SaleStatus.EMITIDA.value: "Emitida",
    SaleStatus.ANULADA.value: "Anulada",
}


class DocumentSeries(Base, TimestampMixin):
    """Serie y correlativo de cada tipo de comprobante."""

    __tablename__ = "document_series"
    __table_args__ = (
        UniqueConstraint("document_type", "series", name="uq_document_series"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    series: Mapped[str] = mapped_column(String(10), nullable=False)
    next_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def document_label(self) -> str:
        return DOCUMENT_TYPE_LABELS.get(self.document_type, self.document_type)

    def format_number(self, number: int) -> str:
        return f"{number:08d}"


class Sale(Base, TimestampMixin):
    """Nota de venta o comprobante emitido en caja (cláusulas 2.8 y 2.9)."""

    __tablename__ = "sales"
    __table_args__ = (
        UniqueConstraint("document_type", "series", "number", name="uq_sale_document"),
        Index("ix_sales_issued_at", "issued_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    series: Mapped[str] = mapped_column(String(10), nullable=False)
    number: Mapped[str] = mapped_column(String(12), nullable=False)

    patient_id: Mapped[int | None] = mapped_column(ForeignKey("patients.id"))
    encounter_id: Mapped[int | None] = mapped_column(ForeignKey("encounters.id"))

    customer_document_type: Mapped[str | None] = mapped_column(String(20))
    customer_document_number: Mapped[str | None] = mapped_column(String(20))
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_address: Mapped[str | None] = mapped_column(String(255))

    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(12), default=SaleStatus.EMITIDA.value, nullable=False, index=True
    )
    payment_method: Mapped[str] = mapped_column(
        String(20), default=PaymentMethod.EFECTIVO.value, nullable=False
    )

    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=ZERO, nullable=False)
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=ZERO, nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=ZERO, nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=ZERO, nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=ZERO, nullable=False)

    notes: Mapped[str | None] = mapped_column(Text)
    cancel_reason: Mapped[str | None] = mapped_column(String(255))

    # Integración con el proveedor de facturación electrónica (cláusula 2.9).
    external_id: Mapped[str | None] = mapped_column(String(80))
    external_status: Mapped[str | None] = mapped_column(String(40))

    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    patient: Mapped[Patient | None] = relationship(lazy="joined")
    items: Mapped[list["SaleItem"]] = relationship(
        back_populates="sale",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SaleItem.id",
    )

    @property
    def document_label(self) -> str:
        return DOCUMENT_TYPE_LABELS.get(self.document_type, self.document_type)

    @property
    def status_label(self) -> str:
        return SALE_STATUS_LABELS.get(self.status, self.status)

    @property
    def payment_label(self) -> str:
        return PAYMENT_METHOD_LABELS.get(self.payment_method, self.payment_method)

    @property
    def full_number(self) -> str:
        return f"{self.series}-{self.number}"

    @property
    def item_count(self) -> int:
        return len(self.items)

    @property
    def is_cancelled(self) -> bool:
        return self.status == SaleStatus.ANULADA.value

    @property
    def is_electronic(self) -> bool:
        return self.document_type in ELECTRONIC_DOCUMENTS


class SaleItem(Base, TimestampMixin):
    """Detalle del comprobante: producto de farmacia o servicio del tarifario."""

    __tablename__ = "sale_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sales.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    service_id: Mapped[int | None] = mapped_column(ForeignKey("medical_services.id"))

    description: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    discount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=ZERO, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=ZERO, nullable=False)

    sale: Mapped[Sale] = relationship(back_populates="items")
    product: Mapped[Product | None] = relationship(lazy="joined")
    service: Mapped[MedicalService | None] = relationship(lazy="joined")

    @property
    def unit(self) -> str:
        return self.product.unit if self.product else "SERVICIO"

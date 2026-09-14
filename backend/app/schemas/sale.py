from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.sale import DocumentType, PaymentMethod
from app.schemas.types import LocalDatetime

# Tipo de documento del cliente exigido por cada comprobante.
FACTURA_REQUIRES_RUC = "La factura requiere RUC y razón social del cliente"


class SeriesBase(BaseModel):
    document_type: DocumentType
    series: str = Field(min_length=2, max_length=10)
    next_number: int = Field(default=1, ge=1, le=99_999_999)
    is_default: bool = False
    is_active: bool = True

    @field_validator("series")
    @classmethod
    def _upper(cls, value: str) -> str:
        return value.strip().upper()


class SeriesCreate(SeriesBase):
    """Alta de una serie de comprobantes."""


class SeriesUpdate(SeriesBase):
    """Actualización de la serie y su correlativo."""


class SeriesRead(SeriesBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_label: str


class SaleItemWrite(BaseModel):
    product_id: int | None = None
    service_id: int | None = None
    description: str | None = Field(default=None, max_length=200)
    quantity: int = Field(gt=0, le=100_000)
    unit_price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    discount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=10, decimal_places=2)

    @model_validator(mode="after")
    def _check_reference(self) -> "SaleItemWrite":
        if self.product_id is None and self.service_id is None and not self.description:
            raise ValueError("Indique un producto, un servicio o una descripción")
        return self


class SaleItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int | None
    service_id: int | None
    description: str
    unit: str
    quantity: int
    unit_price: Decimal
    discount: Decimal
    subtotal: Decimal


class SaleCreate(BaseModel):
    """Emisión de una nota de venta o comprobante."""

    document_type: DocumentType = DocumentType.NOTA_VENTA
    series: str | None = Field(default=None, max_length=10, description="Serie; usa la de por defecto")
    patient_id: int | None = None
    encounter_id: int | None = None

    customer_document_type: str | None = Field(default=None, max_length=20)
    customer_document_number: str | None = Field(default=None, max_length=20)
    customer_name: str | None = Field(default=None, max_length=200)
    customer_address: str | None = Field(default=None, max_length=255)

    payment_method: PaymentMethod = PaymentMethod.EFECTIVO
    issued_at: datetime | None = None
    apply_tax: bool = Field(default=True, description="Desglosa el IGV configurado")
    notes: str | None = Field(default=None, max_length=1000)
    items: list[SaleItemWrite] = Field(min_length=1)

    @field_validator("customer_name", "customer_address", "notes", mode="before")
    @classmethod
    def _clean(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = " ".join(value.split())
            return cleaned or None
        return value

    @model_validator(mode="after")
    def _check_customer(self) -> "SaleCreate":
        if self.patient_id is None and not self.customer_name:
            raise ValueError("Indique el paciente o el nombre del cliente")
        if self.document_type is DocumentType.FACTURA:
            if not self.customer_document_number or len(self.customer_document_number) != 11:
                raise ValueError(FACTURA_REQUIRES_RUC)
            self.customer_document_type = "RUC"
        return self


class SaleCancel(BaseModel):
    reason: str = Field(min_length=3, max_length=255)


class SaleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_type: str
    document_label: str
    series: str
    number: str
    full_number: str
    patient_id: int | None
    encounter_id: int | None
    customer_document_type: str | None
    customer_document_number: str | None
    customer_name: str
    customer_address: str | None
    issued_at: LocalDatetime
    status: str
    status_label: str
    is_cancelled: bool
    is_electronic: bool
    payment_method: str
    payment_label: str
    subtotal: Decimal
    tax: Decimal
    discount: Decimal
    total: Decimal
    tax_rate: Decimal
    notes: str | None
    cancel_reason: str | None
    external_id: str | None
    external_status: str | None
    item_count: int
    items: list[SaleItemRead]
    created_at: LocalDatetime


class SaleListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_label: str
    full_number: str
    customer_name: str
    issued_at: LocalDatetime
    payment_label: str
    total: Decimal
    status: str
    status_label: str
    item_count: int


class SalesSummary(BaseModel):
    """Resumen de caja del periodo consultado."""

    date_from: date
    date_to: date
    documents: int
    cancelled: int
    subtotal: float
    tax: float
    total: float
    by_payment_method: dict[str, float]
    by_document_type: dict[str, float]

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.purchase import SupplierDocumentType
from app.schemas.types import LocalDatetime


class _CleanStrings(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def _blank_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = " ".join(value.split())
            return cleaned or None
        return value


class SupplierBase(_CleanStrings):
    tax_id: str | None = Field(default=None, min_length=11, max_length=11)
    business_name: str = Field(min_length=3, max_length=180)
    trade_name: str | None = Field(default=None, max_length=180)
    contact_name: str | None = Field(default=None, max_length=160)
    phone: str | None = Field(default=None, max_length=40)
    email: EmailStr | None = Field(default=None, max_length=160)
    address: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=1000)
    is_active: bool = True

    @field_validator("tax_id")
    @classmethod
    def _check_ruc(cls, value: str | None) -> str | None:
        if value and not value.isdigit():
            raise ValueError("El RUC debe contener solo dígitos")
        return value


class SupplierCreate(SupplierBase):
    """Alta de proveedor."""


class SupplierUpdate(SupplierBase):
    """Actualización de proveedor."""


class SupplierRead(SupplierBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    display_name: str


class PurchaseItemWrite(BaseModel):
    product_id: int
    quantity: int = Field(gt=0, le=1_000_000)
    unit_cost: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    lot: str | None = Field(default=None, max_length=40)
    expiry_date: date | None = None


class PurchaseItemRead(PurchaseItemWrite):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_name: str
    product_code: str
    unit: str
    subtotal: Decimal


class PurchaseBase(BaseModel):
    supplier_id: int
    document_type: SupplierDocumentType = SupplierDocumentType.FACTURA
    series: str | None = Field(default=None, max_length=10)
    number: str | None = Field(default=None, max_length=20)
    issue_date: date
    apply_tax: bool = Field(default=True, description="Agrega el IGV configurado al subtotal")
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("series", "number", "notes", mode="before")
    @classmethod
    def _clean(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = " ".join(value.split())
            return cleaned or None
        return value


class PurchaseCreate(PurchaseBase):
    """Registro de una compra con su detalle."""

    items: list[PurchaseItemWrite] = Field(min_length=1)


class PurchaseUpdate(PurchaseCreate):
    """Corrección de una compra aún en borrador."""


class PurchaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_id: int
    supplier_name: str
    document_type: str
    document_label: str
    series: str | None
    number: str | None
    document_number: str | None
    issue_date: date
    received_at: LocalDatetime | None
    status: str
    status_label: str
    is_editable: bool
    subtotal: Decimal
    tax: Decimal
    total: Decimal
    item_count: int
    total_units: int
    notes: str | None
    cancel_reason: str | None
    items: list[PurchaseItemRead]
    created_at: LocalDatetime


class PurchaseListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    supplier_name: str
    document_label: str
    document_number: str | None
    issue_date: date
    status: str
    status_label: str
    item_count: int
    total: Decimal


class PurchaseStats(BaseModel):
    drafts: int
    received_this_month: int
    amount_this_month: float
    active_suppliers: int

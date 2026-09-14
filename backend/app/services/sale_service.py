from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.datetime import now, to_local, today
from app.models.inventory import MovementReason, MovementType
from app.models.sale import (
    DocumentSeries,
    DocumentType,
    Sale,
    SaleItem,
    SaleStatus,
)
from app.models.user import User
from app.repositories.catalog_repository import MedicalServiceRepository
from app.repositories.encounter_repository import EncounterRepository
from app.repositories.inventory_repository import ProductRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.sale_repository import DocumentSeriesRepository, SaleRepository
from app.schemas.common import Pagination
from app.schemas.sale import SaleCreate, SalesSummary, SeriesCreate, SeriesUpdate
from app.services.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.services.inventory_service import InventoryService
from app.services.settings_service import SettingsService

REFERENCE_TYPE = "SALE"
CENTS = Decimal("0.01")
HUNDRED = Decimal("100")

# Series creadas automáticamente si el establecimiento aún no configuró las suyas.
DEFAULT_SERIES: dict[str, str] = {
    DocumentType.NOTA_VENTA.value: "NV01",
    DocumentType.BOLETA.value: "B001",
    DocumentType.FACTURA.value: "F001",
}


class SaleService:
    """Notas de venta, comprobantes y resumen de caja (cláusulas 2.8 y 2.9)."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.sales = SaleRepository(db)
        self.series = DocumentSeriesRepository(db)
        self.products = ProductRepository(db)
        self.services = MedicalServiceRepository(db)
        self.patients = PatientRepository(db)
        self.encounters = EncounterRepository(db)
        self.inventory = InventoryService(db)

    # --- Series ---------------------------------------------------------
    def list_series(self, *, only_active: bool = False) -> list[DocumentSeries]:
        return self.series.list_all(only_active=only_active)

    def create_series(self, payload: SeriesCreate) -> DocumentSeries:
        if self.series.get_by_series(payload.document_type.value, payload.series) is not None:
            raise ConflictError("Esa serie ya está registrada para el tipo de comprobante")
        series = DocumentSeries(
            document_type=payload.document_type.value,
            series=payload.series,
            next_number=payload.next_number,
            is_default=payload.is_default,
            is_active=payload.is_active,
        )
        if payload.is_default:
            self.series.clear_default(payload.document_type.value)
        return self.series.add(series)

    def update_series(self, series_id: int, payload: SeriesUpdate) -> DocumentSeries:
        series = self.series.get_by_id(series_id)
        if series is None:
            raise NotFoundError("La serie no existe")
        existing = self.series.get_by_series(payload.document_type.value, payload.series)
        if existing is not None and existing.id != series.id:
            raise ConflictError("Esa serie ya está registrada para el tipo de comprobante")

        series.document_type = payload.document_type.value
        series.series = payload.series
        series.next_number = payload.next_number
        series.is_default = payload.is_default
        series.is_active = payload.is_active
        if payload.is_default:
            self.series.clear_default(payload.document_type.value, keep_id=series.id)
        return self.series.save(series)

    # --- Consultas ------------------------------------------------------
    def list_sales(self, **filters) -> tuple[list[Sale], int]:
        pagination: Pagination = filters.pop("pagination")
        return self.sales.search(pagination=pagination, **filters)

    def get(self, sale_id: int) -> Sale:
        sale = self.sales.get_by_id(sale_id)
        if sale is None:
            raise NotFoundError("El comprobante no existe")
        return sale

    def summary(self, date_from: date, date_to: date) -> SalesSummary:
        """Resumen de caja del periodo: totales por medio de pago y documento."""
        sales = self.sales.list_in_range(date_from, date_to)
        issued = [sale for sale in sales if sale.status == SaleStatus.EMITIDA.value]

        by_payment: dict[str, float] = {}
        by_document: dict[str, float] = {}
        for sale in issued:
            by_payment[sale.payment_label] = round(
                by_payment.get(sale.payment_label, 0.0) + float(sale.total), 2
            )
            by_document[sale.document_label] = round(
                by_document.get(sale.document_label, 0.0) + float(sale.total), 2
            )

        return SalesSummary(
            date_from=date_from,
            date_to=date_to,
            documents=len(issued),
            cancelled=len(sales) - len(issued),
            subtotal=round(sum(float(sale.subtotal) for sale in issued), 2),
            tax=round(sum(float(sale.tax) for sale in issued), 2),
            total=round(sum(float(sale.total) for sale in issued), 2),
            by_payment_method=by_payment,
            by_document_type=by_document,
        )

    # --- Emisión --------------------------------------------------------
    def create(self, payload: SaleCreate, actor: User) -> Sale:
        series = self._resolve_series(payload.document_type, payload.series)
        customer = self._resolve_customer(payload)
        issued_at = to_local(payload.issued_at) if payload.issued_at else now()

        sale = Sale(
            document_type=payload.document_type.value,
            series=series.series,
            number=series.format_number(series.next_number),
            patient_id=payload.patient_id,
            encounter_id=self._validate_encounter(payload.encounter_id),
            issued_at=issued_at,
            status=SaleStatus.EMITIDA.value,
            payment_method=payload.payment_method.value,
            notes=payload.notes,
            created_by_id=actor.id,
            **customer,
        )
        sale.items = self._build_items(payload)
        self._apply_totals(sale, payload.apply_tax)

        series.next_number += 1
        self.db.add(series)
        self.db.add(sale)
        self.db.flush()

        for item in sale.items:
            if item.product is not None:
                self.inventory.apply_movement(
                    product=item.product,
                    movement_type=MovementType.SALIDA,
                    reason=MovementReason.VENTA,
                    quantity=item.quantity,
                    reference_type=REFERENCE_TYPE,
                    reference_id=sale.id,
                    notes=f"{sale.document_label} {sale.full_number}",
                    actor=actor,
                    commit=False,
                )

        self.db.commit()
        self.db.refresh(sale)
        return sale

    def cancel(self, sale_id: int, reason: str, actor: User) -> Sale:
        """Anula el comprobante y repone el stock de los productos vendidos."""
        sale = self.get(sale_id)
        if sale.is_cancelled:
            return sale

        for item in sale.items:
            if item.product is not None:
                self.inventory.apply_movement(
                    product=item.product,
                    movement_type=MovementType.ENTRADA,
                    reason=MovementReason.ANULACION,
                    quantity=item.quantity,
                    reference_type=REFERENCE_TYPE,
                    reference_id=sale.id,
                    notes=f"Anulación de {sale.document_label} {sale.full_number}",
                    actor=actor,
                    commit=False,
                )

        sale.status = SaleStatus.ANULADA.value
        sale.cancel_reason = reason
        return self.sales.save(sale)

    # --- Apoyo ----------------------------------------------------------
    def _resolve_series(self, document_type: DocumentType, series: str | None) -> DocumentSeries:
        if series:
            found = self.series.get_by_series(document_type.value, series)
            if found is None:
                raise BusinessRuleError("La serie indicada no está registrada")
            if not found.is_active:
                raise BusinessRuleError("La serie indicada está inactiva")
            return found

        found = self.series.get_default(document_type.value)
        if found is not None:
            return found
        # Primera emisión del tipo de documento: se crea la serie por defecto.
        return self.series.add(
            DocumentSeries(
                document_type=document_type.value,
                series=DEFAULT_SERIES[document_type.value],
                next_number=1,
                is_default=True,
            )
        )

    def _resolve_customer(self, payload: SaleCreate) -> dict[str, str | None]:
        if payload.patient_id is not None:
            patient = self.patients.get_by_id(payload.patient_id)
            if patient is None:
                raise BusinessRuleError("El paciente indicado no existe")
            return {
                "customer_document_type": payload.customer_document_type or patient.document_type,
                "customer_document_number": (
                    payload.customer_document_number or patient.document_number
                ),
                "customer_name": payload.customer_name or patient.display_name,
                "customer_address": payload.customer_address or patient.address,
            }
        return {
            "customer_document_type": payload.customer_document_type,
            "customer_document_number": payload.customer_document_number,
            "customer_name": payload.customer_name or "Cliente varios",
            "customer_address": payload.customer_address,
        }

    def _validate_encounter(self, encounter_id: int | None) -> int | None:
        if encounter_id is not None and self.encounters.get_by_id(encounter_id) is None:
            raise BusinessRuleError("La atención indicada no existe")
        return encounter_id

    def _build_items(self, payload: SaleCreate) -> list[SaleItem]:
        items: list[SaleItem] = []
        # Un producto puede repetirse en varias líneas (precios o descuentos
        # distintos): el stock se contrasta contra el total pedido, no contra
        # cada línea por separado.
        requested: dict[int, int] = {}
        for entry in payload.items:
            product = service = None
            description = entry.description
            unit_price = entry.unit_price

            if entry.product_id is not None:
                product = self.products.get_by_id(entry.product_id)
                if product is None:
                    raise BusinessRuleError("Uno de los productos indicados no existe")
                if not product.is_active:
                    raise BusinessRuleError(f"El producto {product.name} está inactivo")
                requested[product.id] = requested.get(product.id, 0) + entry.quantity
                if product.stock < requested[product.id]:
                    raise BusinessRuleError(
                        f"Stock insuficiente de {product.full_name}: "
                        f"disponible {product.stock}, solicitado {requested[product.id]}"
                    )
                description = description or product.full_name
                unit_price = unit_price if unit_price is not None else product.sale_price
            elif entry.service_id is not None:
                service = self.services.get_by_id(entry.service_id)
                if service is None:
                    raise BusinessRuleError("Uno de los servicios indicados no existe")
                description = description or service.name
                unit_price = unit_price if unit_price is not None else service.price

            if unit_price is None:
                raise BusinessRuleError(f"Indique el precio de «{description}»")

            gross = unit_price * entry.quantity
            if entry.discount > gross:
                raise BusinessRuleError(f"El descuento de «{description}» supera el importe")

            item = SaleItem(
                product_id=product.id if product else None,
                service_id=service.id if service else None,
                description=description,
                quantity=entry.quantity,
                unit_price=unit_price,
                discount=entry.discount,
                subtotal=(gross - entry.discount).quantize(CENTS),
            )
            item.product = product
            item.service = service
            items.append(item)
        return items

    def _apply_totals(self, sale: Sale, apply_tax: bool) -> None:
        """Los precios de lista incluyen IGV: el impuesto se desglosa del total."""
        gross = sum((item.subtotal for item in sale.items), Decimal("0.00")).quantize(CENTS)
        discount = sum((item.discount for item in sale.items), Decimal("0.00")).quantize(CENTS)
        rate = Decimal(str(SettingsService(self.db).get().tax_rate)) if apply_tax else Decimal("0")

        base = (gross / (Decimal("1") + rate / HUNDRED)).quantize(CENTS) if rate else gross
        sale.subtotal = base
        sale.tax = (gross - base).quantize(CENTS)
        sale.discount = discount
        sale.total = gross
        sale.tax_rate = rate

    def revenue_today(self) -> float:
        reference = today()
        return self.sales.revenue_in_range(reference, reference)

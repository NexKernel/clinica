from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import AdminUser, DbSession, PageParams, require_manage, require_view
from app.core.datetime import today
from app.core.permissions import ModuleCode
from app.models import User
from app.schemas.common import Page
from app.schemas.sale import (
    SaleCancel,
    SaleCreate,
    SaleListItem,
    SaleRead,
    SalesSummary,
    SeriesCreate,
    SeriesRead,
    SeriesUpdate,
)
from app.services.sale_service import SaleService

router = APIRouter(prefix="/sales", tags=["sales"])

Viewer = Annotated[User, Depends(require_view(ModuleCode.SALES))]
Manager = Annotated[User, Depends(require_manage(ModuleCode.SALES))]


# --- Series de comprobantes --------------------------------------------
@router.get("/series", response_model=list[SeriesRead])
def list_series(
    db: DbSession, current_user: Viewer, only_active: Annotated[bool, Query()] = False
) -> list[SeriesRead]:
    return [
        SeriesRead.model_validate(item)
        for item in SaleService(db).list_series(only_active=only_active)
    ]


@router.post("/series", response_model=SeriesRead, status_code=status.HTTP_201_CREATED)
def create_series(payload: SeriesCreate, db: DbSession, current_user: AdminUser) -> SeriesRead:
    return SeriesRead.model_validate(SaleService(db).create_series(payload))


@router.put("/series/{series_id}", response_model=SeriesRead)
def update_series(
    series_id: int, payload: SeriesUpdate, db: DbSession, current_user: AdminUser
) -> SeriesRead:
    return SeriesRead.model_validate(SaleService(db).update_series(series_id, payload))


# --- Comprobantes -------------------------------------------------------
@router.get("/summary", response_model=SalesSummary)
def sales_summary(
    db: DbSession,
    current_user: Viewer,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> SalesSummary:
    """Resumen de caja del periodo: totales por medio de pago y documento."""
    reference = today()
    return SaleService(db).summary(date_from or reference, date_to or reference)


@router.get("", response_model=Page[SaleListItem])
def list_sales(
    db: DbSession,
    current_user: Viewer,
    pagination: PageParams,
    search: Annotated[str | None, Query(max_length=120)] = None,
    document_type: Annotated[str | None, Query(max_length=20)] = None,
    sale_status: Annotated[str | None, Query(alias="status", max_length=12)] = None,
    patient_id: Annotated[int | None, Query()] = None,
    payment_method: Annotated[str | None, Query(max_length=20)] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> Page[SaleListItem]:
    items, total = SaleService(db).list_sales(
        term=search,
        document_type=document_type,
        status=sale_status,
        patient_id=patient_id,
        payment_method=payment_method,
        date_from=date_from,
        date_to=date_to,
        pagination=pagination,
    )
    return Page[SaleListItem](
        items=[SaleListItem.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
def create_sale(payload: SaleCreate, db: DbSession, current_user: Manager) -> SaleRead:
    """Emite la nota de venta o comprobante y descuenta el stock vendido."""
    return SaleRead.model_validate(SaleService(db).create(payload, current_user))


@router.get("/{sale_id}", response_model=SaleRead)
def get_sale(sale_id: int, db: DbSession, current_user: Viewer) -> SaleRead:
    return SaleRead.model_validate(SaleService(db).get(sale_id))


@router.post("/{sale_id}/cancel", response_model=SaleRead)
def cancel_sale(
    sale_id: int, payload: SaleCancel, db: DbSession, current_user: Manager
) -> SaleRead:
    return SaleRead.model_validate(SaleService(db).cancel(sale_id, payload.reason, current_user))

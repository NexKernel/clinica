from datetime import date
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import DbSession, PageParams, require_manage, require_view
from app.core.permissions import ModuleCode
from app.models import User
from app.schemas.common import Page
from app.schemas.purchase import (
    PurchaseCreate,
    PurchaseListItem,
    PurchaseRead,
    PurchaseStats,
    PurchaseUpdate,
    SupplierCreate,
    SupplierRead,
    SupplierUpdate,
)
from app.services.purchase_service import PurchaseService

router = APIRouter(prefix="/purchases", tags=["purchases"])

Viewer = Annotated[User, Depends(require_view(ModuleCode.PURCHASES))]
Manager = Annotated[User, Depends(require_manage(ModuleCode.PURCHASES))]


# --- Proveedores --------------------------------------------------------
@router.get("/suppliers", response_model=Page[SupplierRead])
def list_suppliers(
    db: DbSession,
    current_user: Viewer,
    pagination: PageParams,
    search: Annotated[str | None, Query(max_length=120)] = None,
    is_active: Annotated[bool | None, Query()] = None,
) -> Page[SupplierRead]:
    items, total = PurchaseService(db).list_suppliers(
        term=search, is_active=is_active, pagination=pagination
    )
    return Page[SupplierRead](
        items=[SupplierRead.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/suppliers/active", response_model=list[SupplierRead])
def list_active_suppliers(db: DbSession, current_user: Viewer) -> list[SupplierRead]:
    return [
        SupplierRead.model_validate(item)
        for item in PurchaseService(db).list_active_suppliers()
    ]


@router.post("/suppliers", response_model=SupplierRead, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreate, db: DbSession, current_user: Manager
) -> SupplierRead:
    return SupplierRead.model_validate(PurchaseService(db).create_supplier(payload))


@router.put("/suppliers/{supplier_id}", response_model=SupplierRead)
def update_supplier(
    supplier_id: int, payload: SupplierUpdate, db: DbSession, current_user: Manager
) -> SupplierRead:
    return SupplierRead.model_validate(PurchaseService(db).update_supplier(supplier_id, payload))


# --- Compras ------------------------------------------------------------
@router.get("/stats", response_model=PurchaseStats)
def purchase_stats(db: DbSession, current_user: Viewer) -> PurchaseStats:
    return PurchaseService(db).stats()


@router.get("", response_model=Page[PurchaseListItem])
def list_purchases(
    db: DbSession,
    current_user: Viewer,
    pagination: PageParams,
    search: Annotated[str | None, Query(max_length=120)] = None,
    supplier_id: Annotated[int | None, Query()] = None,
    purchase_status: Annotated[str | None, Query(alias="status", max_length=12)] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> Page[PurchaseListItem]:
    items, total = PurchaseService(db).list_purchases(
        term=search,
        supplier_id=supplier_id,
        status=purchase_status,
        date_from=date_from,
        date_to=date_to,
        pagination=pagination,
    )
    return Page[PurchaseListItem](
        items=[PurchaseListItem.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("", response_model=PurchaseRead, status_code=status.HTTP_201_CREATED)
def create_purchase(
    payload: PurchaseCreate, db: DbSession, current_user: Manager
) -> PurchaseRead:
    return PurchaseRead.model_validate(PurchaseService(db).create(payload, current_user))


@router.get("/{purchase_id}", response_model=PurchaseRead)
def get_purchase(purchase_id: int, db: DbSession, current_user: Viewer) -> PurchaseRead:
    return PurchaseRead.model_validate(PurchaseService(db).get(purchase_id))


@router.put("/{purchase_id}", response_model=PurchaseRead)
def update_purchase(
    purchase_id: int, payload: PurchaseUpdate, db: DbSession, current_user: Manager
) -> PurchaseRead:
    return PurchaseRead.model_validate(PurchaseService(db).update(purchase_id, payload))


@router.post("/{purchase_id}/receive", response_model=PurchaseRead)
def receive_purchase(purchase_id: int, db: DbSession, current_user: Manager) -> PurchaseRead:
    """Ingresa los productos de la compra al inventario."""
    return PurchaseRead.model_validate(PurchaseService(db).receive(purchase_id, current_user))


@router.post("/{purchase_id}/cancel", response_model=PurchaseRead)
def cancel_purchase(
    purchase_id: int,
    db: DbSession,
    current_user: Manager,
    reason: Annotated[str, Body(embed=True, min_length=3, max_length=255)],
) -> PurchaseRead:
    return PurchaseRead.model_validate(
        PurchaseService(db).cancel(purchase_id, reason, current_user)
    )

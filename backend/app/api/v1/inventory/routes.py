from datetime import date
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import DbSession, PageParams, require_manage, require_view
from app.core.permissions import ModuleCode
from app.models import User
from app.schemas.common import Page
from app.schemas.inventory import (
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    ExpiringItem,
    InventoryStats,
    LowStockItem,
    MovementCreate,
    MovementRead,
    ProductCreate,
    ProductRead,
    ProductSummary,
    ProductUpdate,
    StockAdjustment,
)
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory", tags=["inventory"])

Viewer = Annotated[User, Depends(require_view(ModuleCode.PHARMACY))]
Manager = Annotated[User, Depends(require_manage(ModuleCode.PHARMACY))]


# --- Categorías ---------------------------------------------------------
@router.get("/categories", response_model=list[CategoryRead])
def list_categories(
    db: DbSession, current_user: Viewer, only_active: Annotated[bool, Query()] = False
) -> list[CategoryRead]:
    return [
        CategoryRead.model_validate(item)
        for item in InventoryService(db).list_categories(only_active=only_active)
    ]


@router.post("/categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate, db: DbSession, current_user: Manager
) -> CategoryRead:
    return CategoryRead.model_validate(InventoryService(db).create_category(payload))


@router.put("/categories/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int, payload: CategoryUpdate, db: DbSession, current_user: Manager
) -> CategoryRead:
    return CategoryRead.model_validate(InventoryService(db).update_category(category_id, payload))


# --- Indicadores y alertas ---------------------------------------------
@router.get("/stats", response_model=InventoryStats)
def inventory_stats(db: DbSession, current_user: Viewer) -> InventoryStats:
    return InventoryService(db).stats()


@router.get("/expiring", response_model=list[ExpiringItem])
def expiring_products(
    db: DbSession,
    current_user: Viewer,
    limit: Annotated[int | None, Query(ge=1, le=200)] = None,
) -> list[ExpiringItem]:
    """Productos vencidos o próximos a vencer, con existencias disponibles."""
    return [ExpiringItem.model_validate(item) for item in InventoryService(db).expiring(limit)]


@router.get("/alerts", response_model=list[LowStockItem])
def low_stock_alerts(
    db: DbSession,
    current_user: Viewer,
    limit: Annotated[int | None, Query(ge=1, le=200)] = None,
) -> list[LowStockItem]:
    """Productos que requieren reposición (cláusula 2.6)."""
    return [LowStockItem.model_validate(item) for item in InventoryService(db).low_stock(limit)]


# --- Productos ----------------------------------------------------------
@router.get("/products", response_model=Page[ProductRead])
def list_products(
    db: DbSession,
    current_user: Viewer,
    pagination: PageParams,
    search: Annotated[str | None, Query(max_length=120)] = None,
    kind: Annotated[str | None, Query(max_length=20)] = None,
    category_id: Annotated[int | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    low_stock: Annotated[bool, Query()] = False,
    expiring: Annotated[bool, Query(description="Solo vencidos o por vencer")] = False,
) -> Page[ProductRead]:
    items, total = InventoryService(db).list_products(
        term=search,
        kind=kind,
        category_id=category_id,
        is_active=is_active,
        low_stock=low_stock,
        expiring=expiring,
        pagination=pagination,
    )
    return Page[ProductRead](
        items=[ProductRead.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/products/search", response_model=list[ProductSummary])
def search_products(
    db: DbSession,
    current_user: Viewer,
    term: Annotated[str, Query(min_length=2, max_length=120)],
) -> list[ProductSummary]:
    """Búsqueda incremental usada por recetas, ventas y compras."""
    return [
        ProductSummary.model_validate(item) for item in InventoryService(db).quick_search(term)
    ]


@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: DbSession, current_user: Manager) -> ProductRead:
    return ProductRead.model_validate(InventoryService(db).create_product(payload, current_user))


@router.get("/products/{product_id}", response_model=ProductRead)
def get_product(product_id: int, db: DbSession, current_user: Viewer) -> ProductRead:
    return ProductRead.model_validate(InventoryService(db).get_product(product_id))


@router.put("/products/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int, payload: ProductUpdate, db: DbSession, current_user: Manager
) -> ProductRead:
    return ProductRead.model_validate(InventoryService(db).update_product(product_id, payload))


@router.patch("/products/{product_id}/status", response_model=ProductRead)
def set_product_status(
    product_id: int,
    db: DbSession,
    current_user: Manager,
    is_active: Annotated[bool, Body(embed=True)],
) -> ProductRead:
    return ProductRead.model_validate(
        InventoryService(db).set_product_active(product_id, is_active)
    )


# --- Kardex -------------------------------------------------------------
@router.get("/movements", response_model=Page[MovementRead])
def list_movements(
    db: DbSession,
    current_user: Viewer,
    pagination: PageParams,
    product_id: Annotated[int | None, Query()] = None,
    movement_type: Annotated[str | None, Query(max_length=12)] = None,
    reason: Annotated[str | None, Query(max_length=24)] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> Page[MovementRead]:
    items, total = InventoryService(db).list_movements(
        product_id=product_id,
        movement_type=movement_type,
        reason=reason,
        date_from=date_from,
        date_to=date_to,
        pagination=pagination,
    )
    return Page[MovementRead](
        items=[MovementRead.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.post("/movements", response_model=MovementRead, status_code=status.HTTP_201_CREATED)
def register_movement(
    payload: MovementCreate, db: DbSession, current_user: Manager
) -> MovementRead:
    """Registra una entrada, salida o devolución de almacén."""
    return MovementRead.model_validate(InventoryService(db).register_movement(payload, current_user))


@router.post("/movements/adjust", response_model=MovementRead, status_code=status.HTTP_201_CREATED)
def adjust_stock(
    payload: StockAdjustment, db: DbSession, current_user: Manager
) -> MovementRead:
    """Cuadra el stock del sistema con el conteo físico."""
    return MovementRead.model_validate(InventoryService(db).adjust_stock(payload, current_user))

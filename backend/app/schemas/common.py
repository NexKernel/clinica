from typing import Generic, TypeVar

from pydantic import BaseModel

ItemT = TypeVar("ItemT")

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20


class Page(BaseModel, Generic[ItemT]):
    """Respuesta paginada estándar de los módulos del sistema."""

    items: list[ItemT]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        return max(1, -(-self.total // self.page_size))


class Pagination(BaseModel):
    """Parámetros de paginación ya normalizados."""

    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE

    @classmethod
    def of(cls, page: int, page_size: int) -> "Pagination":
        return cls(
            page=max(page, 1),
            page_size=min(max(page_size, 1), MAX_PAGE_SIZE),
        )

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class OperationResult(BaseModel):
    """Respuesta simple para operaciones sin cuerpo de dominio."""

    detail: str

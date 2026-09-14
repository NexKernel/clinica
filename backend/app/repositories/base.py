from typing import Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
from app.schemas.common import Pagination

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Operaciones comunes a todos los repositorios del sistema."""

    model: type[ModelT]

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, entity_id: int) -> ModelT | None:
        return self.db.get(self.model, entity_id)

    def add(self, entity: ModelT) -> ModelT:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def save(self, entity: ModelT) -> ModelT:
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def delete(self, entity: ModelT) -> None:
        self.db.delete(entity)
        self.db.commit()

    def flush(self, entity: ModelT) -> ModelT:
        """Persiste sin cerrar la transacción (operaciones con varias tablas)."""
        self.db.add(entity)
        self.db.flush()
        return entity

    def count(self, stmt: Select[tuple[ModelT]]) -> int:
        return self.db.execute(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        ).scalar_one()

    def paginate(
        self, stmt: Select[tuple[ModelT]], pagination: Pagination
    ) -> tuple[list[ModelT], int]:
        total = self.count(stmt)
        page_stmt = stmt.offset(pagination.offset).limit(pagination.page_size)
        items = list(self.db.execute(page_stmt).unique().scalars().all())
        return items, total

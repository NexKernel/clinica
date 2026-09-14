from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.datetime import now
from app.db.base import Base


class AuditLog(Base):
    """Registro básico de acciones relevantes (cláusula 2.10).

    Se anota toda operación que crea, modifica o elimina información, con el
    usuario que la realizó, el módulo afectado y el resultado de la operación.
    """

    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_user_date", "user_id", "created_at"),
        Index("ix_audit_logs_module_date", "module", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    username: Mapped[str | None] = mapped_column(String(50))
    role: Mapped[str | None] = mapped_column(String(32))

    action: Mapped[str] = mapped_column(String(10), nullable=False)
    module: Mapped[str] = mapped_column(String(40), nullable=False)
    path: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(40))
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(45))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, nullable=False, index=True
    )

    @property
    def succeeded(self) -> bool:
        return self.status_code < 400

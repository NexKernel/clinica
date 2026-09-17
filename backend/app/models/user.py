from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from typing import TYPE_CHECKING

from app.db.base import Base, TimestampMixin
from app.models.role import Role

if TYPE_CHECKING:
    from app.models.practitioner import Practitioner


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Cuenta técnica sembrada desde FIRST_ADMIN_*: su credencial vive en el
    # entorno, así que no se lista ni se administra desde la aplicación.
    is_system: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    role_ref: Mapped[Role] = relationship(back_populates="users", lazy="joined")
    # Ficha de profesional de quien atiende. La crea el alta de usuario para los
    # perfiles asistenciales; los administrativos no tienen.
    practitioner_ref: Mapped["Practitioner | None"] = relationship(
        "Practitioner", lazy="joined", viewonly=True
    )

    @property
    def practitioner_id(self) -> int | None:
        """Con qué ficha firma sus atenciones, o None si no atiende."""
        return self.practitioner_ref.id if self.practitioner_ref else None

    @property
    def role(self) -> str:
        return self.role_ref.code

    @property
    def role_name(self) -> str:
        return self.role_ref.name

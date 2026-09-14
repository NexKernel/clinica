from datetime import time

from sqlalchemy import Boolean, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.catalog import Specialty

WEEKDAY_LABELS: dict[int, str] = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}


class Practitioner(Base, TimestampMixin):
    """Profesional que atiende en el policlínico (agenda por médico)."""

    __tablename__ = "practitioners"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), unique=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    specialty_id: Mapped[int | None] = mapped_column(ForeignKey("specialties.id"))
    license_number: Mapped[str | None] = mapped_column(String(30))
    document_number: Mapped[str | None] = mapped_column(String(20))
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(160))
    slot_minutes: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    specialty: Mapped[Specialty | None] = relationship(lazy="joined")
    schedules: Mapped[list["PractitionerSchedule"]] = relationship(
        back_populates="practitioner",
        cascade="all, delete-orphan",
        order_by="PractitionerSchedule.weekday, PractitionerSchedule.start_time",
        lazy="selectin",
    )

    @property
    def specialty_name(self) -> str | None:
        return self.specialty.name if self.specialty else None

    @property
    def display_name(self) -> str:
        return f"{self.full_name} — {self.specialty_name}" if self.specialty else self.full_name


class PractitionerSchedule(Base, TimestampMixin):
    """Bloque de atención semanal del profesional."""

    __tablename__ = "practitioner_schedules"
    __table_args__ = (
        UniqueConstraint(
            "practitioner_id", "weekday", "start_time", name="uq_schedule_practitioner_block"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    practitioner_id: Mapped[int] = mapped_column(
        ForeignKey("practitioners.id", ondelete="CASCADE"), nullable=False, index=True
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    practitioner: Mapped[Practitioner] = relationship(back_populates="schedules")

    @property
    def weekday_label(self) -> str:
        return WEEKDAY_LABELS.get(self.weekday, "")

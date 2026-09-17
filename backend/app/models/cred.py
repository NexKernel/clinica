from datetime import date

from sqlalchemy import Date, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.patient import Patient
from app.models.practitioner import Practitioner


class CredEntry(Base, TimestampMixin):
    """Una prestación del carné efectivamente aplicada a un niño.

    Las cuatro rejillas del carné en papel —plan de atención, inmunizaciones,
    controles y tamizajes— registran siempre lo mismo: qué se dio, en qué
    dosis, cuándo y quién. Por eso son una sola tabla y no cuatro: lo que las
    distingue es el `item_code`, que apunta al catálogo de `app/core/cred.py`.

    Las prestaciones con fecha en el calendario —una vacuna, un control— no se
    repiten, y la restricción única lo garantiza. Las que sí se repiten, como
    la entrega de micronutrientes o una sesión educativa, llevan `sequence`
    para poder anotarlas tantas veces como haga falta.
    """

    __tablename__ = "cred_entries"
    __table_args__ = (
        UniqueConstraint("patient_id", "item_code", "sequence", name="uq_cred_entry_item"),
        Index("ix_cred_entries_patient_date", "patient_id", "performed_on"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Código del catálogo. No es clave foránea: el catálogo es código, no datos,
    # y un registro ya hecho debe sobrevivir a que el esquema nacional cambie.
    item_code: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # Distingue entregas repetidas de una misma prestación; 1 para las únicas.
    sequence: Mapped[int] = mapped_column(default=1, nullable=False)

    performed_on: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # Resultado de un tamizaje («Hb 11.2 g/dL», «Negativo»); vacío en el resto.
    result: Mapped[str | None] = mapped_column(String(160))
    notes: Mapped[str | None] = mapped_column(Text)

    practitioner_id: Mapped[int | None] = mapped_column(ForeignKey("practitioners.id"))
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    patient: Mapped[Patient] = relationship(lazy="joined")
    practitioner: Mapped[Practitioner | None] = relationship(lazy="joined")

    @property
    def practitioner_name(self) -> str | None:
        return self.practitioner.full_name if self.practitioner else None

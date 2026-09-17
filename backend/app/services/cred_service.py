from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.cred import (
    BY_CODE,
    CATALOG,
    CRED_KIND_LABELS,
    CRED_STATUS_LABELS,
    MAX_AGE_MONTHS,
    CredItem,
    CredKind,
    CredStatus,
    status_for,
)
from app.core.datetime import today
from app.models import CredEntry, Patient, User
from app.schemas.cred import (
    CredCard,
    CredCatalogItem,
    CredEntryCreate,
    CredEntryRead,
    CredEntryWrite,
    CredSection,
    CredSlot,
)

# Prestaciones que se entregan más de una vez: una sesión educativa o un
# reparto de micronutrientes se repiten a lo largo del programa, a diferencia
# de una vacuna, que en el calendario ocurre una sola vez por dosis.
REPEATABLE_KINDS = frozenset({CredKind.SUPLEMENTO.value, CredKind.PRESTACION.value})


def _age_months(patient: Patient) -> int | None:
    """Edad en meses cumplidos; None si no se registró la fecha de nacimiento."""
    if patient.birth_date is None:
        return None
    hoy = today()
    meses = (hoy.year - patient.birth_date.year) * 12 + hoy.month - patient.birth_date.month
    if hoy.day < patient.birth_date.day:
        meses -= 1
    return max(meses, 0)


def _age_label(meses: int | None) -> str:
    if meses is None:
        return "Sin fecha de nacimiento"
    if meses < 1:
        return "Recién nacido"
    if meses < 24:
        return f"{meses} {'mes' if meses == 1 else 'meses'}"
    anios, resto = divmod(meses, 12)
    if resto == 0:
        return f"{anios} años"
    return f"{anios} años {resto} {'mes' if resto == 1 else 'meses'}"


class CredService:
    """Carné de atención integral de la niña y el niño.

    El carné no se guarda: se compone cada vez cruzando el calendario del
    MINSA con lo que consta aplicado. Así un cambio del esquema nacional se
    refleja en todos los carnés sin migrar un solo registro.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    # --- Lectura ---------------------------------------------------------

    def card(self, patient: Patient) -> CredCard:
        meses = _age_months(patient)
        por_codigo = self._entries_by_code(patient.id)

        secciones: list[CredSection] = []
        total_aplicadas = total_atrasadas = total_pendientes = 0

        for kind in CredKind:
            slots: list[CredSlot] = []
            aplicadas = atrasadas = 0

            for item in (i for i in CATALOG if i.kind == kind):
                registros = por_codigo.get(item.code, [])
                estado = status_for(item, meses, bool(registros))
                if estado is CredStatus.APLICADA:
                    aplicadas += 1
                elif estado is CredStatus.ATRASADA:
                    atrasadas += 1
                elif estado is CredStatus.PENDIENTE:
                    total_pendientes += 1

                slots.append(
                    CredSlot(
                        item_code=item.code,
                        group=item.group,
                        label=item.label,
                        dose=item.dose,
                        due_month=item.due_month,
                        status=estado.value,
                        status_label=CRED_STATUS_LABELS[estado.value],
                        records_result=item.records_result,
                        entries=[CredEntryRead.model_validate(e) for e in registros],
                    )
                )

            total_aplicadas += aplicadas
            total_atrasadas += atrasadas
            secciones.append(
                CredSection(
                    kind=kind.value,
                    label=CRED_KIND_LABELS[kind.value],
                    slots=slots,
                    applied=aplicadas,
                    overdue=atrasadas,
                )
            )

        from app.schemas.patient import PatientSummary

        return CredCard(
            patient=PatientSummary.model_validate(patient),
            age_months=meses,
            age_label=_age_label(meses),
            in_program=meses is not None and meses <= MAX_AGE_MONTHS,
            sections=secciones,
            applied=total_aplicadas,
            overdue=total_atrasadas,
            pending=total_pendientes,
        )

    def catalog(self, patient_id: int) -> list[CredCatalogItem]:
        """Catálogo para el selector, marcando lo que ya no se puede repetir."""
        aplicados = set(self._entries_by_code(patient_id))
        return [
            CredCatalogItem(
                code=item.code,
                kind=item.kind.value,
                kind_label=CRED_KIND_LABELS[item.kind.value],
                group=item.group,
                label=item.label,
                dose=item.dose,
                due_month=item.due_month,
                records_result=item.records_result,
                repeatable=self._is_repeatable(item),
                already_applied=item.code in aplicados,
            )
            for item in CATALOG
        ]

    def _entries_by_code(self, patient_id: int) -> dict[str, list[CredEntry]]:
        stmt = (
            select(CredEntry)
            .where(CredEntry.patient_id == patient_id)
            .order_by(CredEntry.performed_on, CredEntry.sequence)
        )
        agrupado: dict[str, list[CredEntry]] = defaultdict(list)
        for entry in self.db.execute(stmt).unique().scalars().all():
            agrupado[entry.item_code].append(entry)
        return agrupado

    @staticmethod
    def _is_repeatable(item: CredItem) -> bool:
        return item.kind.value in REPEATABLE_KINDS

    # --- Escritura -------------------------------------------------------

    def create(self, payload: CredEntryCreate, actor: User) -> CredEntry:
        item = self._item(payload.item_code)
        patient = self.db.get(Patient, payload.patient_id)
        if patient is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "El paciente no existe")

        self._check_date(payload, patient)

        existentes = self._entries_by_code(patient.id).get(item.code, [])
        if existentes and not self._is_repeatable(item):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"{item.label} ya figura aplicada el "
                f"{existentes[0].performed_on.strftime('%d/%m/%Y')}.",
            )

        entry = CredEntry(
            patient_id=patient.id,
            item_code=item.code,
            sequence=len(existentes) + 1,
            performed_on=payload.performed_on,
            result=payload.result,
            notes=payload.notes,
            practitioner_id=payload.practitioner_id,
            created_by_id=actor.id,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def update(self, entry_id: int, payload: CredEntryWrite) -> CredEntry:
        entry = self._entry(entry_id)
        item = self._item(payload.item_code)
        if item.code != entry.item_code:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Para cambiar la prestación, elimine el registro y vuelva a anotarlo.",
            )
        self._check_date(payload, entry.patient)

        entry.performed_on = payload.performed_on
        entry.result = payload.result
        entry.notes = payload.notes
        entry.practitioner_id = payload.practitioner_id
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def delete(self, entry_id: int) -> None:
        entry = self._entry(entry_id)
        self.db.delete(entry)
        self.db.commit()

    # --- Apoyo -----------------------------------------------------------

    def _entry(self, entry_id: int) -> CredEntry:
        entry = self.db.get(CredEntry, entry_id)
        if entry is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "El registro no existe")
        return entry

    @staticmethod
    def _item(code: str) -> CredItem:
        item = BY_CODE.get(code)
        if item is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Prestación no reconocida")
        return item

    @staticmethod
    def _check_date(payload: CredEntryWrite, patient: Patient) -> None:
        """Una prestación no se aplica en el futuro ni antes de nacer."""
        if payload.performed_on > today():
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "La fecha de la prestación no puede ser futura"
            )
        if patient.birth_date and payload.performed_on < patient.birth_date:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "La fecha es anterior al nacimiento del paciente",
            )


# --- Hoja impresa ---------------------------------------------------------
# El carné se lleva a casa, así que se imprime con el mismo membrete que el
# resto de documentos. No es una plantilla del catálogo porque su contenido no
# vive en el documento sino en `cred_entries`: se compone cada vez.

_ESTILO_CARNE = """
.cred-grid { width: 100%; border-collapse: collapse; margin: 4px 0 10px; font-size: 8.5pt; }
.cred-grid th, .cred-grid td { border: 1px solid var(--doc-rule); padding: 3px 5px; }
.cred-grid th { background: #eef7f6; text-align: left; font-size: 8pt; text-transform: uppercase; }
.cred-grid td.g { font-weight: 600; white-space: nowrap; width: 1%; }
.cred-box { display: inline-block; min-width: 54px; margin: 1px; padding: 2px 4px;
            border: 1px solid var(--doc-rule); border-radius: 3px; text-align: center; font-size: 7.5pt; }
.cred-box b { display: block; font-size: 8pt; }
.cred-ok { background: #e8f6ef; border-color: #7fbf9c; }
.cred-late { background: #fdecea; border-color: #e0a19a; }
.cred-due { background: #fdf6e3; border-color: #dcc48a; }
"""


def render_card_sheet(card: "CredCard") -> str:
    """Las cuatro rejillas del carné, para imprimir y entregar a la madre."""
    import html as _html

    clase = {
        "APLICADA": "cred-box cred-ok",
        "ATRASADA": "cred-box cred-late",
        "PENDIENTE": "cred-box cred-due",
        "FUTURA": "cred-box",
    }

    partes: list[str] = [
        f"<style>{_ESTILO_CARNE}</style>",
        '<table class="doc-grid">'
        f'<tr><td class="k">Edad</td><td>{_html.escape(card.age_label)}</td>'
        f'<td class="k">Aplicadas</td><td>{card.applied}</td></tr>'
        f'<tr><td class="k">Atrasadas</td><td>{card.overdue}</td>'
        f'<td class="k">Le tocan</td><td>{card.pending}</td></tr>'
        "</table>",
    ]

    for section in card.sections:
        grupos: dict[str, list] = {}
        for slot in section.slots:
            grupos.setdefault(slot.group, []).append(slot)

        filas = []
        for grupo, slots in grupos.items():
            casillas = []
            for slot in slots:
                registro = slot.entries[0] if slot.entries else None
                pie = (
                    registro.performed_on.strftime("%d/%m/%y")
                    if registro
                    else _html.escape(slot.status_label)
                )
                extra = f" ({len(slot.entries)})" if len(slot.entries) > 1 else ""
                casillas.append(
                    f'<span class="{clase[slot.status]}">'
                    f"<b>{_html.escape(slot.dose or slot.label)}</b>{pie}{extra}</span>"
                )
            filas.append(
                f'<tr><td class="g">{_html.escape(grupo)}</td><td>{"".join(casillas)}</td></tr>'
            )

        partes.append(
            f"<h2>{_html.escape(section.label)}</h2>"
            f'<table class="cred-grid">{"".join(filas)}</table>'
        )

    return "".join(partes)

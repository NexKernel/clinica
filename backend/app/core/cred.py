"""Calendario de atención integral de la niña y el niño (CRED).

El carné en papel son cuatro rejillas —plan de atención, inmunizaciones,
controles de crecimiento y tamizajes— que en el fondo registran lo mismo: qué
prestación se dio, en qué dosis u orden, y en qué fecha. Aquí está el catálogo
de lo que corresponde a cada edad; el registro de lo efectivamente aplicado
vive en `cred_entries`.

Lo que convierte un registro en un carné es justamente este catálogo: sin él
solo habría una lista de fechas, y no se podría decir qué falta ni qué venció.

Las edades se expresan en meses cumplidos y salen del esquema nacional del
MINSA tal como lo recoge el formato de la clínica. `grace_months` es el margen
que se concede antes de considerar atrasada una prestación: por debajo de él la
prestación figura como pendiente, y por encima como atrasada.

Del plan de atención integral solo se declaran aquí las prestaciones que no
tienen rejilla propia. Las vacunas, los controles, los tamizajes y los
suplementos ya se registran en su grilla y duplicarlos como fila del plan
obligaría a anotar dos veces lo mismo.
"""

from dataclasses import dataclass
from enum import StrEnum


class CredKind(StrEnum):
    VACUNA = "VACUNA"
    CONTROL = "CONTROL"
    TAMIZAJE = "TAMIZAJE"
    SUPLEMENTO = "SUPLEMENTO"
    PRESTACION = "PRESTACION"


CRED_KIND_LABELS: dict[str, str] = {
    CredKind.VACUNA.value: "Inmunizaciones",
    CredKind.CONTROL.value: "Control de crecimiento y desarrollo",
    CredKind.TAMIZAJE.value: "Tamizajes",
    CredKind.SUPLEMENTO.value: "Micronutrientes",
    CredKind.PRESTACION.value: "Plan de atención integral",
}


@dataclass(frozen=True, slots=True)
class CredItem:
    """Una prestación del calendario, con la edad a la que corresponde."""

    kind: CredKind
    code: str
    group: str
    label: str
    dose: str
    due_month: int | None
    grace_months: int = 2
    records_result: bool = False

    @property
    def title(self) -> str:
        return f"{self.group} · {self.dose}" if self.dose else self.group


def _vacuna(code: str, group: str, dose: str, due_month: int) -> CredItem:
    return CredItem(CredKind.VACUNA, code, group, f"{group} {dose}".strip(), dose, due_month)


def _control(code: str, group: str, dose: str, due_month: int) -> CredItem:
    return CredItem(CredKind.CONTROL, code, group, f"{group} · {dose}", dose, due_month, grace_months=1)


def _tamizaje(code: str, group: str, dose: str, due_month: int) -> CredItem:
    return CredItem(
        CredKind.TAMIZAJE, code, group, f"{group} · {dose}", dose, due_month,
        grace_months=3, records_result=True,
    )


# --- Inmunizaciones -------------------------------------------------------
# Esquema nacional: la dosis se identifica por su orden, y el recién nacido
# recibe BCG y hepatitis B antes de salir del establecimiento.

VACUNAS: tuple[CredItem, ...] = (
    _vacuna("BCG", "BCG", "RN", 0),
    _vacuna("HVB", "HVB", "RN", 0),
    _vacuna("PENTA-1", "Pentavalente", "1ª", 2),
    _vacuna("PENTA-2", "Pentavalente", "2ª", 4),
    _vacuna("PENTA-3", "Pentavalente", "3ª", 6),
    _vacuna("APO-1", "APO / IPV", "1ª", 2),
    _vacuna("APO-2", "APO / IPV", "2ª", 4),
    _vacuna("APO-3", "APO / IPV", "3ª", 6),
    _vacuna("ROTA-1", "Rotavirus", "1ª", 2),
    _vacuna("ROTA-2", "Rotavirus", "2ª", 4),
    _vacuna("NEUMO-1", "Neumococo", "1ª", 2),
    _vacuna("NEUMO-2", "Neumococo", "2ª", 4),
    _vacuna("NEUMO-3", "Neumococo", "3ª", 12),
    _vacuna("FLU-1", "Influenza", "1ª", 6),
    _vacuna("FLU-2", "Influenza", "2ª", 7),
    _vacuna("SPR-1", "SPR", "1ª", 12),
    _vacuna("SPR-R", "SPR", "R", 18),
    _vacuna("AMA", "AMA", "Única", 15),
    _vacuna("DTP-1R", "DTP", "1.º R", 18),
    _vacuna("DTP-2R", "DTP", "2.º R", 48),
)


# --- Controles de crecimiento y desarrollo --------------------------------
# Cantidad de controles por banda de edad, según el formato: cuatro en el
# período neonatal, once en el resto del primer año, seis en el segundo, cuatro
# por año hasta los cuatro, y uno anual de los cinco a los nueve.

def _serie_controles() -> tuple[CredItem, ...]:
    items: list[CredItem] = []

    for orden in range(1, 5):
        items.append(_control(f"CRED-RN-{orden}", "Recién nacido", f"{orden}.º", 0))

    for orden in range(1, 12):
        items.append(_control(f"CRED-M{orden}", "Menor de 1 año", f"{orden}.º", orden))

    for orden in range(1, 7):
        items.append(_control(f"CRED-1A-{orden}", "1 año", f"{orden}.º", 12 + (orden - 1) * 2))

    for anio in (2, 3, 4):
        for orden in range(1, 5):
            items.append(
                _control(
                    f"CRED-{anio}A-{orden}", f"{anio} años", f"{orden}.º",
                    anio * 12 + (orden - 1) * 3,
                )
            )

    for anio in range(5, 10):
        items.append(_control(f"CRED-{anio}A", f"{anio} años", "Anual", anio * 12))

    return tuple(items)


CONTROLES: tuple[CredItem, ...] = _serie_controles()


# --- Tamizajes ------------------------------------------------------------

def _anios(cantidad: int) -> str:
    """«1 año» y no «1 años»: el carné lo lee la madre, no un informe."""
    return "1 año" if cantidad == 1 else f"{cantidad} años"


def _serie_tamizajes() -> tuple[CredItem, ...]:
    items: list[CredItem] = [
        _tamizaje("TAM-NEO", "Neonatal (THS y otros)", "RN", 0),
    ]
    # Anemia y parasitosis se repiten una vez al año; el formato las tabula
    # desde el primer año de vida hasta los nueve.
    for anio in range(0, 10):
        etiqueta = "< 1 año" if anio == 0 else _anios(anio)
        items.append(_tamizaje(f"TAM-ANEMIA-{anio}", "Descarte de anemia", etiqueta, max(anio * 12, 6)))
    for anio in range(1, 10):
        items.append(
            _tamizaje(f"TAM-PARASITO-{anio}", "Descarte de parasitosis", _anios(anio), anio * 12)
        )
    return tuple(items)


TAMIZAJES: tuple[CredItem, ...] = _serie_tamizajes()


# --- Micronutrientes ------------------------------------------------------
# La suplementación es continua y no se agota en una fecha, así que no lleva
# edad de vencimiento: se registran las entregas y se cuentan.

SUPLEMENTOS: tuple[CredItem, ...] = (
    CredItem(CredKind.SUPLEMENTO, "SUP-HIERRO", "Hierro", "Hierro", "", None),
    CredItem(CredKind.SUPLEMENTO, "SUP-VITA", "Vitamina A", "Vitamina A", "", None),
    CredItem(CredKind.SUPLEMENTO, "SUP-MMN", "Multimicronutrientes", "Multimicronutrientes", "", None),
    CredItem(CredKind.SUPLEMENTO, "SUP-OTRO", "Otros", "Otros", "", None),
)


# --- Plan de atención integral -------------------------------------------
# Solo lo que no tiene rejilla propia: el resto del plan se cubre con las
# grillas de vacunas, controles, tamizajes y suplementos.

PRESTACIONES: tuple[CredItem, ...] = (
    CredItem(CredKind.PRESTACION, "PRE-ETI", "Estimulación temprana", "Sesión de estimulación temprana", "", None),
    CredItem(CredKind.PRESTACION, "PRE-NUT", "Consejería nutricional", "Consejería nutricional", "", None),
    CredItem(CredKind.PRESTACION, "PRE-ODO", "Salud bucal", "Atención odontológica", "", None),
    CredItem(CredKind.PRESTACION, "PRE-BAR", "Salud bucal", "Aplicación de barnices o sellantes", "", None),
    CredItem(CredKind.PRESTACION, "PRE-REC", "Salud bucal", "Tratamiento recuperativo", "", None),
    CredItem(CredKind.PRESTACION, "PRE-PAT", "Patologías prevalentes", "Atención de patologías prevalentes", "", None),
    CredItem(CredKind.PRESTACION, "PRE-EDU", "Sesiones", "Sesión educativa", "", None),
    CredItem(CredKind.PRESTACION, "PRE-DEM", "Sesiones", "Sesión demostrativa", "", None),
    CredItem(CredKind.PRESTACION, "PRE-VIS", "Visita familiar", "Visita familiar integral", "", None),
    CredItem(CredKind.PRESTACION, "PRE-OTRO", "Otros", "Otra prestación", "", None),
)


CATALOG: tuple[CredItem, ...] = VACUNAS + CONTROLES + TAMIZAJES + SUPLEMENTOS + PRESTACIONES

BY_CODE: dict[str, CredItem] = {item.code: item for item in CATALOG}

# Edad a partir de la cual el carné deja de seguirse: el programa acompaña al
# niño hasta que cumple diez años.
MAX_AGE_MONTHS = 120


class CredStatus(StrEnum):
    APLICADA = "APLICADA"
    PENDIENTE = "PENDIENTE"
    ATRASADA = "ATRASADA"
    FUTURA = "FUTURA"


CRED_STATUS_LABELS: dict[str, str] = {
    CredStatus.APLICADA.value: "Aplicada",
    CredStatus.PENDIENTE.value: "Le toca",
    CredStatus.ATRASADA.value: "Atrasada",
    CredStatus.FUTURA.value: "Más adelante",
}


def status_for(item: CredItem, age_months: int | None, applied: bool) -> CredStatus:
    """En qué situación está una prestación para un niño de esa edad.

    Sin fecha de nacimiento no se puede juzgar el calendario, así que lo no
    aplicado queda como pendiente en lugar de inventar un atraso.
    """
    if applied:
        return CredStatus.APLICADA
    if item.due_month is None or age_months is None:
        return CredStatus.PENDIENTE
    if age_months < item.due_month:
        return CredStatus.FUTURA
    if age_months > item.due_month + item.grace_months:
        return CredStatus.ATRASADA
    return CredStatus.PENDIENTE

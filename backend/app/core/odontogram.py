"""Odontograma: del dato guardado al gráfico que sale impreso en la ficha.

El formato en papel de la clínica trae un diagrama de piezas dentales que se
marca a mano. Aquí se dibuja en SVG, que es lo que corresponde: la hoja del
documento la imprime el navegador con su propia regla `@page`, sin librería de
PDF de por medio, así que un vectorial sale a la resolución de la impresora y
no pixelado como saldría una imagen.

El dato viaja como un diccionario por pieza, en notación FDI:

    {"18": {"o": "caries", "m": "obturado"}, "26": {"pieza": "ausente"}}

Las claves de cara son las cinco caras de la pieza (`o` oclusal o incisal, `m`
mesial, `d` distal, `v` vestibular, `l` lingual o palatina) y `pieza` es el
estado de la pieza entera. El catálogo de hallazgos se repite en el frontend
(`frontend/src/features/documents/components/Odontogram.tsx`): si cambia uno,
cambia el otro, porque el gráfico que se marca y el que se imprime tienen que
decir lo mismo.

El código de color es el que el personal ya lee sobre el papel: rojo lo que
falta tratar, azul lo que ya está tratado.
"""

from typing import Any

ROJO = "#c0392b"
AZUL = "#1f5fa8"
AZUL_CLARO = "#8ab4e0"
TRAZO = "#94a3b8"
TINTA = "#1f2937"

# Hallazgos que se marcan sobre una cara concreta de la pieza.
SURFACE_FINDINGS: dict[str, tuple[str, str]] = {
    "caries": ("Caries", ROJO),
    "obturado": ("Obturado", AZUL),
    "sellante": ("Sellante", AZUL_CLARO),
}

# Hallazgos que afectan a la pieza entera. El segundo valor es la marca que se
# dibuja encima: `x` son las dos diagonales, `o` un círculo, y cualquier otra
# cosa se pinta como esa letra centrada.
TOOTH_FINDINGS: dict[str, tuple[str, str, str]] = {
    "extraccion": ("Exodoncia indicada", ROJO, "x"),
    "ausente": ("Pieza ausente", AZUL, "x"),
    "corona": ("Corona", AZUL, "o"),
    "implante": ("Implante", AZUL, "I"),
    "erupcion": ("En erupción", AZUL, "E"),
    "remanente": ("Remanente radicular", ROJO, "R"),
}

# Filas tal como se leen en el diagrama, con la línea media al centro. El
# paciente se mira de frente: el cuadrante 1 queda a la izquierda de la hoja.
PERMANENT_ROWS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("18", "17", "16", "15", "14", "13", "12", "11"),
     ("21", "22", "23", "24", "25", "26", "27", "28")),
    (("48", "47", "46", "45", "44", "43", "42", "41"),
     ("31", "32", "33", "34", "35", "36", "37", "38")),
)

DECIDUOUS_ROWS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("55", "54", "53", "52", "51"), ("61", "62", "63", "64", "65")),
    (("85", "84", "83", "82", "81"), ("71", "72", "73", "74", "75")),
)

# Geometría de una pieza: un cuadrado partido en cuatro trapecios y un centro.
CELL = 28
GAP = 2
PITCH = CELL + GAP
MIDLINE = 14
INSET = 9
INNER = CELL - INSET

# Alturas del diagrama. Se declaran de una vez y no por incrementos porque el
# frontend dibuja el mismo gráfico y las dos versiones tienen que cuadrar; el
# bloque deciduo empieza lejos de la hilera permanente para que su rótulo no
# caiga encima de la numeración de abajo.
Y_TITULO_PERMANENTE = 10
Y_PERMANENTE_SUPERIOR = 24
Y_PERMANENTE_INFERIOR = 56
Y_TITULO_DECIDUO = 112
Y_DECIDUO_SUPERIOR = 132
Y_DECIDUO_INFERIOR = 164
Y_LEYENDA = 218

# Desplazamiento de la numeración respecto del borde de la pieza.
NUM_ARRIBA = 3
NUM_ABAJO = 9

_TRAPEZOIDS: dict[str, str] = {
    "arriba": f"0,0 {CELL},0 {INNER},{INSET} {INSET},{INSET}",
    "derecha": f"{CELL},0 {CELL},{CELL} {INNER},{INNER} {INNER},{INSET}",
    "abajo": f"0,{CELL} {INSET},{INNER} {INNER},{INNER} {CELL},{CELL}",
    "izquierda": f"0,0 {INSET},{INSET} {INSET},{INNER} 0,{CELL}",
}


def _surface_slots(tooth: str) -> dict[str, str]:
    """Qué trapecio le toca a cada cara, según el cuadrante de la pieza.

    En el maxilar superior la cara vestibular queda hacia arriba de la hoja y
    la palatina hacia abajo; en el inferior es al revés. La mesial siempre
    apunta a la línea media, que en el diagrama está al centro.
    """
    quadrant = tooth[0]
    superior = quadrant in ("1", "2", "5", "6")
    izquierda_de_la_hoja = quadrant in ("1", "4", "5", "8")

    return {
        "v": "arriba" if superior else "abajo",
        "l": "abajo" if superior else "arriba",
        "m": "derecha" if izquierda_de_la_hoja else "izquierda",
        "d": "izquierda" if izquierda_de_la_hoja else "derecha",
    }


def _tooth_svg(tooth: str, marks: dict[str, Any], x: float, y: float) -> str:
    """Una pieza con sus caras pintadas y, si toca, la marca de pieza entera."""
    slots = _surface_slots(tooth)
    piezas: list[str] = [f'<g transform="translate({x},{y})">']

    # Caras: primero el relleno que corresponda, luego el contorno.
    for cara, slot in slots.items():
        finding = marks.get(cara)
        _, color = SURFACE_FINDINGS.get(finding, ("", "none"))
        piezas.append(
            f'<polygon points="{_TRAPEZOIDS[slot]}" fill="{color}"'
            f' stroke="{TRAZO}" stroke-width="0.6" />'
        )

    oclusal = marks.get("o")
    _, color = SURFACE_FINDINGS.get(oclusal, ("", "none"))
    piezas.append(
        f'<rect x="{INSET}" y="{INSET}" width="{INNER - INSET}" height="{INNER - INSET}"'
        f' fill="{color}" stroke="{TRAZO}" stroke-width="0.6" />'
    )

    estado = marks.get("pieza")
    if estado in TOOTH_FINDINGS:
        _, color, marca = TOOTH_FINDINGS[estado]
        if marca == "x":
            piezas.append(
                f'<path d="M2,2 L{CELL - 2},{CELL - 2} M{CELL - 2},2 L2,{CELL - 2}"'
                f' stroke="{color}" stroke-width="2" fill="none" />'
            )
        elif marca == "o":
            piezas.append(
                f'<circle cx="{CELL / 2}" cy="{CELL / 2}" r="{CELL / 2 - 1}"'
                f' stroke="{color}" stroke-width="2" fill="none" />'
            )
        else:
            piezas.append(
                f'<text x="{CELL / 2}" y="{CELL / 2 + 4}" text-anchor="middle"'
                f' font-size="13" font-weight="700" fill="{color}">{marca}</text>'
            )

    piezas.append("</g>")
    return "".join(piezas)


def _row_svg(
    row: tuple[tuple[str, ...], tuple[str, ...]],
    data: dict[str, Any],
    origin_x: float,
    y: float,
    numeros_arriba: bool,
) -> str:
    """Una hilera de piezas con su numeración, partida por la línea media."""
    partes: list[str] = []
    num_y = y - NUM_ARRIBA if numeros_arriba else y + CELL + NUM_ABAJO

    for mitad, piezas in enumerate(row):
        for i, tooth in enumerate(piezas):
            # El paso ya arrastra la separación entre piezas, así que se
            # descuenta para que el hueco de la línea media mida MIDLINE.
            salto = len(row[0]) * PITCH + MIDLINE - GAP
            x = origin_x + mitad * salto + i * PITCH
            marks = data.get(tooth) or {}
            if not isinstance(marks, dict):
                marks = {}
            partes.append(_tooth_svg(tooth, marks, x, y))
            partes.append(
                f'<text x="{x + CELL / 2}" y="{num_y}" text-anchor="middle"'
                f' font-size="7.5" fill="{TINTA}">{tooth}</text>'
            )
    return "".join(partes)


def _legend_svg(y: float, width: float) -> str:
    """Leyenda del código de color, para que la hoja se lea sin explicación."""
    entradas = [(label, color, None) for label, color in SURFACE_FINDINGS.values()]
    entradas += [(label, color, marca) for label, color, marca in TOOTH_FINDINGS.values()]

    partes = [f'<line x1="0" y1="{y - 8}" x2="{width}" y2="{y - 8}" stroke="{TRAZO}" stroke-width="0.6" />']
    x = 0.0
    fila = y
    for label, color, marca in entradas:
        if x > width - 118:
            x = 0.0
            fila += 14
        if marca == "x":
            partes.append(
                f'<path d="M{x},{fila - 7} L{x + 9},{fila + 2} M{x + 9},{fila - 7} L{x},{fila + 2}"'
                f' stroke="{color}" stroke-width="1.6" fill="none" />'
            )
        elif marca == "o":
            partes.append(
                f'<circle cx="{x + 4.5}" cy="{fila - 2.5}" r="4.5" stroke="{color}"'
                f' stroke-width="1.6" fill="none" />'
            )
        elif marca:
            partes.append(
                f'<text x="{x + 4.5}" y="{fila + 1}" text-anchor="middle" font-size="9"'
                f' font-weight="700" fill="{color}">{marca}</text>'
            )
        else:
            partes.append(
                f'<rect x="{x}" y="{fila - 7}" width="9" height="9" fill="{color}"'
                f' stroke="{TRAZO}" stroke-width="0.6" />'
            )
        partes.append(
            f'<text x="{x + 13}" y="{fila + 1}" font-size="7.5" fill="{TINTA}">{label}</text>'
        )
        x += 118
    return "".join(partes), fila


def render_odontogram(value: Any) -> str:
    """SVG del odontograma a partir del dato guardado en el documento."""
    data: dict[str, Any] = value if isinstance(value, dict) else {}

    # 16 (o 10) piezas más el hueco de la línea media, sin la separación
    # sobrante que el paso añade al final de cada mitad.
    ancho_permanente = 16 * PITCH + MIDLINE - 2 * GAP
    ancho_deciduo = 10 * PITCH + MIDLINE - 2 * GAP
    sangria_decidua = (ancho_permanente - ancho_deciduo) / 2

    partes: list[str] = [
        f'<text x="0" y="{Y_TITULO_PERMANENTE}" font-size="8" font-weight="700"'
        f' fill="{TINTA}">DENTICIÓN PERMANENTE</text>',
        _row_svg(PERMANENT_ROWS[0], data, 0, Y_PERMANENTE_SUPERIOR, numeros_arriba=True),
        _row_svg(PERMANENT_ROWS[1], data, 0, Y_PERMANENTE_INFERIOR, numeros_arriba=False),
        f'<text x="{sangria_decidua}" y="{Y_TITULO_DECIDUO}" font-size="8" font-weight="700"'
        f' fill="{TINTA}">DENTICIÓN DECIDUA</text>',
        _row_svg(DECIDUOUS_ROWS[0], data, sangria_decidua, Y_DECIDUO_SUPERIOR, numeros_arriba=True),
        _row_svg(DECIDUOUS_ROWS[1], data, sangria_decidua, Y_DECIDUO_INFERIOR, numeros_arriba=False),
    ]

    leyenda, ultima_fila = _legend_svg(Y_LEYENDA, ancho_permanente)
    partes.append(leyenda)
    alto = ultima_fila + 10

    return (
        f'<div class="doc-odontogram"><svg viewBox="0 0 {ancho_permanente} {alto}"'
        f' width="100%" role="img" aria-label="Odontograma"'
        ' xmlns="http://www.w3.org/2000/svg">'
        + "".join(partes)
        + "</svg></div>"
    )

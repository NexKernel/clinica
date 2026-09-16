"""Catálogo inicial de plantillas de documentos (carpeta `formatos_clinica`).

Cada formato en papel se transcribe una sola vez a HTML con marcadores. El
criterio al modelarlo es constante:

* la biometría y los datos que conviene comparar entre controles se declaran
  como campos discretos, para que queden consultables;
* los hallazgos narrativos se declaran como campos de texto con el valor normal
  ya cargado por defecto, que es como se usa el formato impreso.

Ningún dato del establecimiento, del médico ni de la fecha se escribe aquí:
todos provienen del contexto de fusión, para que no se repita el problema de
los formatos en Word, que traían quemados el nombre del médico, su CMP, la
dirección y hasta el año.

Las plantillas se versionan por código. Para cambiar el texto de un documento
no se edita la entrada existente: se agrega otra con `version` mayor, y la
anterior queda desactivada pero disponible para los documentos ya emitidos.
"""

import logging
from typing import Any, NamedTuple

from sqlalchemy.orm import Session

from app.models.document import DocumentFamily, DocumentTemplate
from app.repositories.document_repository import DocumentTemplateRepository

logger = logging.getLogger(__name__)

INFORME = DocumentFamily.INFORME.value
FICHA = DocumentFamily.FICHA.value
CONSENTIMIENTO = DocumentFamily.CONSENTIMIENTO.value
ADMINISTRATIVO = DocumentFamily.ADMINISTRATIVO.value


def opts(*values: str) -> list[dict[str, str]]:
    """Opciones cuyo valor y etiqueta coinciden."""
    return [{"value": value, "label": value} for value in values]


SI_NO = opts("No", "Sí")
NORMAL_ALTERADO = opts("Aspecto normal", "Alterado")
NORMAL_ALTERADO_SIMPLE = opts("Normal", "Alterado")
NEGATIVO_POSITIVO = opts("Negativo", "Positivo")
AUSENTE_PRESENTE = opts("Ausente", "Presente")
SIN_LESIONES = opts("Sin lesiones", "Con lesiones")
ORIENTADO = opts("Orientado", "Desorientado")

# El perfil biofísico puntúa cada parámetro con 0 o 2; la etiqueta explica el
# valor para que quien llena la ficha no tenga que recordar la escala.
BIOPHYSICAL_OPTIONS = [
    {"value": "0", "label": "0 — Ausente"},
    {"value": "2", "label": "2 — Presente"},
]

ESTADO_PACIENTE = opts("Estable", "Inestable", "Crítico", "Con necesidad especial")

# Escala de Glasgow: cada respuesta lleva su puntaje en la etiqueta y el total
# lo calcula el formulario, en lugar de anotarse a mano como en la hoja actual.
GLASGOW_OCULAR = [
    {"value": "4", "label": "4 — Espontánea"},
    {"value": "3", "label": "3 — A la orden verbal"},
    {"value": "2", "label": "2 — Al dolor"},
    {"value": "1", "label": "1 — Sin respuesta"},
]
GLASGOW_VERBAL = [
    {"value": "5", "label": "5 — Orientado"},
    {"value": "4", "label": "4 — Confuso"},
    {"value": "3", "label": "3 — Palabras inapropiadas"},
    {"value": "2", "label": "2 — Sonidos incomprensibles"},
    {"value": "1", "label": "1 — Sin respuesta"},
]
GLASGOW_MOTORA = [
    {"value": "6", "label": "6 — Obedece órdenes"},
    {"value": "5", "label": "5 — Localiza el dolor"},
    {"value": "4", "label": "4 — Retirada al dolor"},
    {"value": "3", "label": "3 — Flexión anormal"},
    {"value": "2", "label": "2 — Extensión anormal"},
    {"value": "1", "label": "1 — Sin respuesta"},
]


# --- Bloques comunes ------------------------------------------------------
# El membrete lo aporta la hoja (app/core/templating.py); aquí solo va la
# cabecera de identificación que cada formato repite.

HEADER_CLINICAL = """<table class="doc-grid">
<tr><td class="k">Paciente</td><td>{{ paciente.nombre_completo }}</td>
    <td class="k">Historia</td><td>{{ paciente.historia }}</td></tr>
<tr><td class="k">Documento</td><td>{{ paciente.tipo_documento }} {{ paciente.documento }}</td>
    <td class="k">Edad</td><td>{{ paciente.edad }}</td></tr>
<tr><td class="k">Fecha</td><td>{{ fecha.hoy }}</td>
    <td class="k">Hora</td><td>{{ fecha.hora }}</td></tr>
<tr><td class="k">Médico</td><td colspan="3">{{ profesional.nombre }} &nbsp;·&nbsp; CMP {{ profesional.cmp }}</td></tr>
</table>"""

SIGN_DOCTOR = """<div class="doc-signatures">
<div class="sign"><div class="line"></div>
<div class="role">{{ profesional.nombre }}</div>
<div class="hint">Médico responsable · CMP {{ profesional.cmp }}</div></div>
</div>"""

SIGN_PATIENT_DOCTOR = """<div class="doc-signatures">
<div class="sign"><div class="line"></div>
<div class="role">Firma del paciente</div>
<div class="hint">{{ paciente.nombre_completo }} · {{ paciente.tipo_documento }} {{ paciente.documento }}</div></div>
<div class="sign"><div class="line"></div>
<div class="role">Firma del médico</div>
<div class="hint">{{ profesional.nombre }} · CMP {{ profesional.cmp }}</div></div>
</div>"""

PLACE_AND_DATE = '<p style="text-align:right">{{ fecha.lugar_larga }}</p>'

ECHO_DISCLAIMER = (
    '<p class="doc-note">La ecografía es un medio de ayuda diagnóstica. '
    "Este informe debe ser interpretado por su médico tratante.</p>"
)

FIELD_MOTIVO: dict[str, Any] = {
    "key": "motivo",
    "label": "Motivo del examen",
    "type": "text",
    "group": "Estudio",
    "wide": True,
}

FIELD_OBSERVACIONES: dict[str, Any] = {
    "key": "observaciones",
    "label": "Observaciones",
    "type": "textarea",
    "group": "Conclusión",
    "default": "Ninguna",
    "wide": True,
}

FIELD_CONCLUSION: dict[str, Any] = {
    "key": "conclusion",
    "label": "Conclusión",
    "type": "textarea",
    "group": "Conclusión",
    "required": True,
    "wide": True,
    "help": "Se copia como resumen del estudio: es lo que el paciente ve en el enlace.",
}

CONCLUSION_BLOCK = """<h2>Observaciones</h2>
<p>{{ campo.observaciones|parrafos }}</p>
<h2>Conclusión</h2>
<p>{{ campo.conclusion|parrafos }}</p>"""


# Biometría fetal y anexos: los repiten el informe obstétrico, el perfil
# biofísico, el Doppler y la morfología, de modo que la hoja impresa y las
# claves guardadas coinciden entre controles de una misma gestante.
FETAL_BIOMETRY_BLOCK = """<h2>Biometría</h2>
<table class="doc-table">
<tr><th>DBP</th><th>CC</th><th>CA</th><th>LF</th></tr>
<tr><td>{{ campo.dbp }} mm</td><td>{{ campo.cc }} mm</td><td>{{ campo.ca }} mm</td><td>{{ campo.lf }} mm</td></tr>
</table>
<table class="doc-grid">
<tr><td class="k">Ponderado fetal</td><td>{{ campo.ponderado }} g &nbsp;±&nbsp; {{ campo.ponderado_error }} g</td>
    <td class="k">Percentil</td><td>{{ campo.percentil }} %</td></tr>
<tr><td class="k">Edad gestacional</td><td colspan="3">{{ campo.edad_gestacional }}</td></tr>
</table>"""

FETAL_ANNEX_BLOCK = """<h2>Placenta y líquido amniótico</h2>
<table class="doc-grid">
<tr><td class="k">Placenta</td><td>{{ campo.placenta }}</td>
    <td class="k">Grado</td><td>{{ campo.placenta_grado }}</td></tr>
<tr><td class="k">Líquido amniótico</td><td>{{ campo.liquido }}</td>
    <td class="k">Pozo mayor</td><td>{{ campo.pozo_mayor }} mm</td></tr>
</table>"""


def fetal_biometry_fields() -> list[dict[str, Any]]:
    return [
        measure("dbp", "DBP (mm)", "Biometría"),
        measure("cc", "CC (mm)", "Biometría"),
        measure("ca", "CA (mm)", "Biometría"),
        measure("lf", "LF (mm)", "Biometría"),
        measure("ponderado", "Ponderado fetal (g)", "Biometría"),
        measure("ponderado_error", "Margen del ponderado (g)", "Biometría"),
        measure("percentil", "Percentil (%)", "Biometría"),
        {"key": "edad_gestacional", "label": "Edad gestacional por ecografía", "type": "text", "group": "Biometría", "placeholder": "35 semanas 3 días", "wide": True},
    ]


def fetal_annex_fields() -> list[dict[str, Any]]:
    return [
        {"key": "placenta", "label": "Placenta · localización", "type": "text", "group": "Placenta y líquido", "placeholder": "Anterior alta"},
        choice("placenta_grado", "Placenta · grado", "Placenta y líquido", opts("0", "I", "II", "III"), "II"),
        choice("liquido", "Líquido amniótico", "Placenta y líquido", opts("Adecuado", "Disminuido", "Aumentado"), "Adecuado"),
        measure("pozo_mayor", "Pozo mayor (mm)", "Placenta y líquido"),
    ]


def echo_report(
    code: str,
    title: str,
    description: str,
    sections: str,
    fields: list[dict[str, Any]],
) -> dict[str, Any]:
    """Informe ecográfico: cabecera, motivo, hallazgos, conclusión y firma."""
    return {
        "code": code,
        "version": 1,
        "family": INFORME,
        "title": title,
        "description": description,
        "study_type": "ECOGRAFIA",
        "requires_signature": True,
        "fields": [FIELD_MOTIVO, *fields, FIELD_OBSERVACIONES, FIELD_CONCLUSION],
        "body": (
            HEADER_CLINICAL
            + "<p><strong>Motivo del examen:</strong> {{ campo.motivo }}</p>"
            + "<p>El estudio ultrasonográfico evidencia:</p>"
            + sections
            + CONCLUSION_BLOCK
            + SIGN_DOCTOR
            + ECHO_DISCLAIMER
        ),
    }


def measure(key: str, label: str, group: str, default: str | None = None) -> dict[str, Any]:
    field: dict[str, Any] = {"key": key, "label": label, "type": "number", "group": group}
    if default is not None:
        field["default"] = default
    return field


def choice(
    key: str, label: str, group: str, options: list[dict[str, str]], default: str
) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "type": "select",
        "group": group,
        "options": options,
        "default": default,
    }


# --- Familia A · Informes de resultado ------------------------------------

ECO_ABDOMINAL = echo_report(
    "ECO-ABD",
    "Informe ecográfico abdominal completo",
    "Hígado, vía biliar, páncreas, bazo, riñones y vejiga",
    """<h2>Hígado</h2>
<table class="doc-grid">
<tr><td class="k">Morfología y movilidad</td><td>{{ campo.higado_morfologia }}</td>
    <td class="k">Parénquima</td><td>{{ campo.higado_parenquima }}</td></tr>
<tr><td class="k">Ecogenicidad</td><td>{{ campo.higado_ecogenicidad }}</td>
    <td class="k">Imágenes expansivas</td><td>{{ campo.higado_expansivas }}</td></tr>
<tr><td class="k">Lóbulo izquierdo</td><td>{{ campo.higado_lob_izq }} mm</td>
    <td class="k">Lóbulo derecho</td><td>{{ campo.higado_lob_der }} mm</td></tr>
<tr><td class="k">Colédoco</td><td colspan="3">{{ campo.coledoco }} mm de diámetro</td></tr>
</table>

<h2>Vesícula biliar</h2>
<table class="doc-grid">
<tr><td class="k">Forma</td><td>{{ campo.vesicula_forma }}</td>
    <td class="k">Paredes</td><td>{{ campo.vesicula_paredes }}</td></tr>
<tr><td class="k">Contenido anecoico</td><td>{{ campo.vesicula_contenido }}</td>
    <td class="k">Barro biliar</td><td>{{ campo.vesicula_barro }}</td></tr>
<tr><td class="k">Cálculos</td><td>{{ campo.vesicula_calculos }}</td>
    <td class="k">Diámetro transverso</td><td>{{ campo.vesicula_diametro }} mm (V.N. &lt; 40 mm)</td></tr>
</table>

<h2>Páncreas y bazo</h2>
<table class="doc-grid">
<tr><td class="k">Páncreas</td><td colspan="3">{{ campo.pancreas }} — cabeza {{ campo.pancreas_cabeza }} mm ·
    cuerpo {{ campo.pancreas_cuerpo }} mm</td></tr>
<tr><td class="k">Bazo</td><td colspan="3">{{ campo.bazo }} — {{ campo.bazo_longitud }} mm de longitud ·
    {{ campo.bazo_ap }} mm de diámetro anteroposterior</td></tr>
<tr><td class="k">Aorta, cava y porta</td><td colspan="3">{{ campo.grandes_vasos }}</td></tr>
</table>

<h2>Riñones</h2>
<table class="doc-table">
<tr><th></th><th>Riñón derecho</th><th>Riñón izquierdo</th></tr>
<tr><td>Morfología y ecogenicidad</td><td>{{ campo.rd_morfologia }}</td><td>{{ campo.ri_morfologia }}</td></tr>
<tr><td>Medidas</td><td>{{ campo.rd_medidas }}</td><td>{{ campo.ri_medidas }}</td></tr>
<tr><td>Hidronefrosis</td><td>{{ campo.rd_hidronefrosis }}</td><td>{{ campo.ri_hidronefrosis }}</td></tr>
<tr><td>Litiasis</td><td>{{ campo.rd_calculos }}</td><td>{{ campo.ri_calculos }}</td></tr>
</table>

<h2>Vejiga y cavidad abdominal</h2>
<table class="doc-grid">
<tr><td class="k">Repleción</td><td>{{ campo.vejiga_replecion }}</td>
    <td class="k">Paredes</td><td>{{ campo.vejiga_paredes }}</td></tr>
<tr><td class="k">Volumen premiccional</td><td>{{ campo.vejiga_volumen }} cc</td>
    <td class="k">Líquido libre</td><td>{{ campo.liquido_libre }}</td></tr>
</table>""",
    [
        choice("higado_morfologia", "Hígado · morfología y movilidad", "Hígado", opts("Normal", "Alterada"), "Normal"),
        choice("higado_parenquima", "Hígado · parénquima", "Hígado", opts("Homogéneo", "Heterogéneo"), "Homogéneo"),
        choice("higado_ecogenicidad", "Hígado · ecogenicidad", "Hígado", opts("Normal", "Aumentada", "Disminuida"), "Normal"),
        choice("higado_expansivas", "Hígado · imágenes expansivas", "Hígado", SI_NO, "No"),
        measure("higado_lob_izq", "Lóbulo izquierdo (mm)", "Hígado"),
        measure("higado_lob_der", "Lóbulo derecho (mm)", "Hígado"),
        measure("coledoco", "Colédoco (mm)", "Hígado"),
        choice("vesicula_forma", "Vesícula · forma", "Vesícula biliar", opts("Piriforme", "Alterada"), "Piriforme"),
        choice("vesicula_paredes", "Vesícula · paredes", "Vesícula biliar", opts("Regulares y delgadas", "Engrosadas", "Irregulares"), "Regulares y delgadas"),
        choice("vesicula_contenido", "Contenido anecoico", "Vesícula biliar", opts("Sí", "No"), "Sí"),
        choice("vesicula_barro", "Barro biliar", "Vesícula biliar", SI_NO, "No"),
        choice("vesicula_calculos", "Cálculos en su interior", "Vesícula biliar", SI_NO, "No"),
        measure("vesicula_diametro", "Diámetro transverso (mm)", "Vesícula biliar"),
        choice("pancreas", "Páncreas · morfología y ecogenicidad", "Páncreas y bazo", opts("Normal", "Alterado"), "Normal"),
        measure("pancreas_cabeza", "Cabeza (mm)", "Páncreas y bazo"),
        measure("pancreas_cuerpo", "Cuerpo (mm)", "Páncreas y bazo"),
        choice("bazo", "Bazo · morfología y ecogenicidad", "Páncreas y bazo", opts("Normal", "Alterado"), "Normal"),
        measure("bazo_longitud", "Bazo · longitud (mm)", "Páncreas y bazo"),
        measure("bazo_ap", "Bazo · diámetro A/P (mm)", "Páncreas y bazo"),
        choice("grandes_vasos", "Aorta, cava y porta", "Páncreas y bazo", opts("Calibres normales", "Alterados"), "Calibres normales"),
        choice("rd_morfologia", "Riñón derecho · morfología", "Riñones", opts("Normal", "Alterada"), "Normal"),
        {"key": "rd_medidas", "label": "Riñón derecho · medidas", "type": "text", "group": "Riñones", "placeholder": "110 x 50 mm"},
        choice("rd_hidronefrosis", "Riñón derecho · hidronefrosis", "Riñones", SI_NO, "No"),
        choice("rd_calculos", "Riñón derecho · litiasis", "Riñones", SI_NO, "No"),
        choice("ri_morfologia", "Riñón izquierdo · morfología", "Riñones", opts("Normal", "Alterada"), "Normal"),
        {"key": "ri_medidas", "label": "Riñón izquierdo · medidas", "type": "text", "group": "Riñones", "placeholder": "110 x 50 mm"},
        choice("ri_hidronefrosis", "Riñón izquierdo · hidronefrosis", "Riñones", SI_NO, "No"),
        choice("ri_calculos", "Riñón izquierdo · litiasis", "Riñones", SI_NO, "No"),
        choice("vejiga_replecion", "Vejiga · repleción", "Vejiga", opts("Buena", "Poca", "Vacua"), "Buena"),
        choice("vejiga_paredes", "Vejiga · paredes", "Vejiga", opts("Normales", "Engrosadas"), "Normales"),
        measure("vejiga_volumen", "Volumen premiccional (cc)", "Vejiga"),
        choice("liquido_libre", "Líquido libre abdominal", "Vejiga", SI_NO, "No"),
    ],
)

ECO_TIROIDES = echo_report(
    "ECO-TIR",
    "Informe ecográfico de tiroides",
    "Lóbulos, istmo y volumen glandular",
    """<h2>Lóbulo derecho</h2>
<table class="doc-grid">
<tr><td class="k">Ecoestructura</td><td>{{ campo.ld_ecoestructura }}</td>
    <td class="k">Imágenes expansivas</td><td>{{ campo.ld_expansivas }}</td></tr>
<tr><td class="k">Medidas</td><td colspan="3">{{ campo.ld_largo }} × {{ campo.ld_ancho }} × {{ campo.ld_ap }} mm ·
    volumen {{ campo.ld_volumen }} cc</td></tr>
<tr><td class="k">Descripción</td><td colspan="3">{{ campo.ld_descripcion }}</td></tr>
</table>

<h2>Lóbulo izquierdo</h2>
<table class="doc-grid">
<tr><td class="k">Ecoestructura</td><td>{{ campo.li_ecoestructura }}</td>
    <td class="k">Imágenes expansivas</td><td>{{ campo.li_expansivas }}</td></tr>
<tr><td class="k">Medidas</td><td colspan="3">{{ campo.li_largo }} × {{ campo.li_ancho }} × {{ campo.li_ap }} mm ·
    volumen {{ campo.li_volumen }} cc</td></tr>
<tr><td class="k">Descripción</td><td colspan="3">{{ campo.li_descripcion }}</td></tr>
</table>

<h2>Istmo</h2>
<p>Grosor de {{ campo.istmo }} mm (valor de referencia: 4 a 6 mm).</p>""",
    [
        choice("ld_ecoestructura", "Lóbulo derecho · ecoestructura", "Lóbulo derecho", opts("Homogénea", "Heterogénea"), "Homogénea"),
        choice("ld_expansivas", "Lóbulo derecho · imágenes expansivas", "Lóbulo derecho", SI_NO, "No"),
        measure("ld_largo", "Largo (mm)", "Lóbulo derecho"),
        measure("ld_ancho", "Ancho (mm)", "Lóbulo derecho"),
        measure("ld_ap", "Anteroposterior (mm)", "Lóbulo derecho"),
        measure("ld_volumen", "Volumen (cc)", "Lóbulo derecho"),
        {"key": "ld_descripcion", "label": "Lóbulo derecho · descripción", "type": "text", "group": "Lóbulo derecho", "wide": True},
        choice("li_ecoestructura", "Lóbulo izquierdo · ecoestructura", "Lóbulo izquierdo", opts("Homogénea", "Heterogénea"), "Homogénea"),
        choice("li_expansivas", "Lóbulo izquierdo · imágenes expansivas", "Lóbulo izquierdo", SI_NO, "No"),
        measure("li_largo", "Largo (mm)", "Lóbulo izquierdo"),
        measure("li_ancho", "Ancho (mm)", "Lóbulo izquierdo"),
        measure("li_ap", "Anteroposterior (mm)", "Lóbulo izquierdo"),
        measure("li_volumen", "Volumen (cc)", "Lóbulo izquierdo"),
        {"key": "li_descripcion", "label": "Lóbulo izquierdo · descripción", "type": "text", "group": "Lóbulo izquierdo", "wide": True},
        measure("istmo", "Istmo · grosor (mm)", "Istmo"),
    ],
)

ECO_OBSTETRICA = echo_report(
    "ECO-OBS",
    "Informe ecográfico obstétrico",
    "Biometría fetal, ponderado, placenta y líquido amniótico",
    """<h2>Evaluación fetal</h2>
<table class="doc-grid">
<tr><td class="k">Visualización</td><td>{{ campo.visualizacion }}</td>
    <td class="k">Situación y presentación</td><td>{{ campo.situacion }}</td></tr>
<tr><td class="k">Latido cardíaco fetal</td><td>{{ campo.lcf }} lpm</td>
    <td class="k">FUR</td><td>{{ campo.fur }}</td></tr>
</table>

"""
    + FETAL_BIOMETRY_BLOCK
    + """

"""
    + FETAL_ANNEX_BLOCK,
    [
        choice("visualizacion", "Visualización", "Evaluación fetal", opts("Adecuada", "Limitada"), "Adecuada"),
        {"key": "situacion", "label": "Situación y presentación", "type": "text", "group": "Evaluación fetal", "placeholder": "Longitudinal cefálico, dorso izquierdo"},
        measure("lcf", "Latido cardíaco fetal (lpm)", "Evaluación fetal"),
        {"key": "fur", "label": "Fecha de última regla", "type": "date", "group": "Evaluación fetal"},
        *fetal_biometry_fields(),
        *fetal_annex_fields(),
    ],
)

ECO_TRANSVAGINAL = echo_report(
    "ECO-TV",
    "Informe ecográfico transvaginal",
    "Útero, endometrio, cérvix, ovarios y saco de Douglas",
    """<h2>Útero</h2>
<table class="doc-grid">
<tr><td class="k">FUR</td><td>{{ campo.fur }}</td>
    <td class="k">Posición</td><td>{{ campo.posicion }}</td></tr>
<tr><td class="k">Medidas</td><td>{{ campo.utero_medidas }}</td>
    <td class="k">Miometrio</td><td>{{ campo.miometrio }}</td></tr>
<tr><td class="k">Bordes</td><td>{{ campo.bordes }}</td>
    <td class="k">Endometrio</td><td>{{ campo.endometrio }}, grosor {{ campo.endometrio_grosor }} mm</td></tr>
<tr><td class="k">Cérvix</td><td colspan="3">{{ campo.cervix }} — {{ campo.cervix_longitud }} mm</td></tr>
</table>

<h2>Anexos</h2>
<table class="doc-grid">
<tr><td class="k">Ovario derecho</td><td>{{ campo.ovario_derecho }}</td>
    <td class="k">Ovario izquierdo</td><td>{{ campo.ovario_izquierdo }}</td></tr>
<tr><td class="k">Saco de Douglas</td><td colspan="3">{{ campo.douglas }}</td></tr>
</table>""",
    [
        {"key": "fur", "label": "Fecha de última regla", "type": "date", "group": "Útero"},
        choice("posicion", "Posición", "Útero", opts("Anteversoflexo", "Retroversoflexo", "Intermedio"), "Anteversoflexo"),
        {"key": "utero_medidas", "label": "Medidas del útero", "type": "text", "group": "Útero", "placeholder": "70 × 40 × 45 mm"},
        choice("miometrio", "Miometrio", "Útero", opts("Homogéneo", "Heterogéneo"), "Homogéneo"),
        choice("bordes", "Bordes", "Útero", opts("Regulares", "Irregulares"), "Regulares"),
        choice("endometrio", "Endometrio", "Útero", opts("Hiperecogénico", "Hipoecogénico", "Trilaminar"), "Hiperecogénico"),
        measure("endometrio_grosor", "Endometrio · grosor (mm)", "Útero"),
        choice("cervix", "Cérvix", "Útero", opts("De aspecto normal", "Alterado"), "De aspecto normal"),
        measure("cervix_longitud", "Cérvix · longitud (mm)", "Útero"),
        {"key": "ovario_derecho", "label": "Ovario derecho", "type": "text", "group": "Anexos", "placeholder": "30 × 20 mm, sin alteraciones"},
        {"key": "ovario_izquierdo", "label": "Ovario izquierdo", "type": "text", "group": "Anexos", "placeholder": "30 × 20 mm, sin alteraciones"},
        choice("douglas", "Saco de Douglas", "Anexos", opts("Libre, no obturado. No líquido libre", "Con líquido libre"), "Libre, no obturado. No líquido libre"),
    ],
)

ECO_MAMAS = echo_report(
    "ECO-MAM",
    "Informe ecográfico de mamas",
    "Parénquima mamario, nódulos y regiones axilares",
    """<h2>Mama derecha</h2>
<table class="doc-grid">
<tr><td class="k">Parénquima</td><td>{{ campo.md_parenquima }}</td>
    <td class="k">Nódulos</td><td>{{ campo.md_nodulos }}</td></tr>
<tr><td class="k">Conductos</td><td>{{ campo.md_conductos }}</td>
    <td class="k">Axila</td><td>{{ campo.md_axila }}</td></tr>
<tr><td class="k">Hallazgos</td><td colspan="3">{{ campo.md_hallazgos }}</td></tr>
</table>

<h2>Mama izquierda</h2>
<table class="doc-grid">
<tr><td class="k">Parénquima</td><td>{{ campo.mi_parenquima }}</td>
    <td class="k">Nódulos</td><td>{{ campo.mi_nodulos }}</td></tr>
<tr><td class="k">Conductos</td><td>{{ campo.mi_conductos }}</td>
    <td class="k">Axila</td><td>{{ campo.mi_axila }}</td></tr>
<tr><td class="k">Hallazgos</td><td colspan="3">{{ campo.mi_hallazgos }}</td></tr>
</table>

<p><strong>Categoría BI-RADS:</strong> {{ campo.birads }}</p>""",
    [
        choice("md_parenquima", "Mama derecha · parénquima", "Mama derecha", opts("Fibroglandular homogéneo", "Heterogéneo", "Graso"), "Fibroglandular homogéneo"),
        choice("md_nodulos", "Mama derecha · nódulos", "Mama derecha", SI_NO, "No"),
        choice("md_conductos", "Mama derecha · conductos", "Mama derecha", opts("No dilatados", "Dilatados"), "No dilatados"),
        choice("md_axila", "Mama derecha · axila", "Mama derecha", opts("Sin adenopatías", "Con adenopatías"), "Sin adenopatías"),
        {"key": "md_hallazgos", "label": "Mama derecha · hallazgos", "type": "text", "group": "Mama derecha", "wide": True},
        choice("mi_parenquima", "Mama izquierda · parénquima", "Mama izquierda", opts("Fibroglandular homogéneo", "Heterogéneo", "Graso"), "Fibroglandular homogéneo"),
        choice("mi_nodulos", "Mama izquierda · nódulos", "Mama izquierda", SI_NO, "No"),
        choice("mi_conductos", "Mama izquierda · conductos", "Mama izquierda", opts("No dilatados", "Dilatados"), "No dilatados"),
        choice("mi_axila", "Mama izquierda · axila", "Mama izquierda", opts("Sin adenopatías", "Con adenopatías"), "Sin adenopatías"),
        {"key": "mi_hallazgos", "label": "Mama izquierda · hallazgos", "type": "text", "group": "Mama izquierda", "wide": True},
        choice("birads", "Categoría BI-RADS", "Conclusión", opts("0", "1", "2", "3", "4", "5", "6"), "1"),
    ],
)

ECO_RENAL = echo_report(
    "ECO-REN",
    "Informe ecográfico renal y vesical",
    "Riñones, vía urinaria y vejiga",
    """<h2>Riñones</h2>
<table class="doc-table">
<tr><th></th><th>Riñón derecho</th><th>Riñón izquierdo</th></tr>
<tr><td>Morfología y movilidad</td><td>{{ campo.rd_morfologia }}</td><td>{{ campo.ri_morfologia }}</td></tr>
<tr><td>Ecogenicidad</td><td>{{ campo.rd_ecogenicidad }}</td><td>{{ campo.ri_ecogenicidad }}</td></tr>
<tr><td>Medidas</td><td>{{ campo.rd_medidas }}</td><td>{{ campo.ri_medidas }}</td></tr>
<tr><td>Parénquima</td><td>{{ campo.rd_parenquima }} mm</td><td>{{ campo.ri_parenquima }} mm</td></tr>
<tr><td>Hidronefrosis</td><td>{{ campo.rd_hidronefrosis }}</td><td>{{ campo.ri_hidronefrosis }}</td></tr>
<tr><td>Litiasis</td><td>{{ campo.rd_calculos }}</td><td>{{ campo.ri_calculos }}</td></tr>
</table>

<h2>Vejiga</h2>
<table class="doc-grid">
<tr><td class="k">Repleción</td><td>{{ campo.vejiga_replecion }}</td>
    <td class="k">Paredes</td><td>{{ campo.vejiga_paredes }}</td></tr>
<tr><td class="k">Volumen premiccional</td><td>{{ campo.vejiga_volumen }} cc</td>
    <td class="k">Residuo posmiccional</td><td>{{ campo.vejiga_residuo }} cc</td></tr>
</table>""",
    [
        choice("rd_morfologia", "Riñón derecho · morfología", "Riñón derecho", opts("Normal", "Alterada"), "Normal"),
        choice("rd_ecogenicidad", "Riñón derecho · ecogenicidad", "Riñón derecho", opts("Normal", "Aumentada"), "Normal"),
        {"key": "rd_medidas", "label": "Riñón derecho · medidas", "type": "text", "group": "Riñón derecho", "placeholder": "110 × 50 mm"},
        measure("rd_parenquima", "Riñón derecho · parénquima (mm)", "Riñón derecho"),
        choice("rd_hidronefrosis", "Riñón derecho · hidronefrosis", "Riñón derecho", SI_NO, "No"),
        choice("rd_calculos", "Riñón derecho · litiasis", "Riñón derecho", SI_NO, "No"),
        choice("ri_morfologia", "Riñón izquierdo · morfología", "Riñón izquierdo", opts("Normal", "Alterada"), "Normal"),
        choice("ri_ecogenicidad", "Riñón izquierdo · ecogenicidad", "Riñón izquierdo", opts("Normal", "Aumentada"), "Normal"),
        {"key": "ri_medidas", "label": "Riñón izquierdo · medidas", "type": "text", "group": "Riñón izquierdo", "placeholder": "110 × 50 mm"},
        measure("ri_parenquima", "Riñón izquierdo · parénquima (mm)", "Riñón izquierdo"),
        choice("ri_hidronefrosis", "Riñón izquierdo · hidronefrosis", "Riñón izquierdo", SI_NO, "No"),
        choice("ri_calculos", "Riñón izquierdo · litiasis", "Riñón izquierdo", SI_NO, "No"),
        choice("vejiga_replecion", "Vejiga · repleción", "Vejiga", opts("Buena", "Poca", "Vacua"), "Buena"),
        choice("vejiga_paredes", "Vejiga · paredes", "Vejiga", opts("Normales", "Engrosadas"), "Normales"),
        measure("vejiga_volumen", "Volumen premiccional (cc)", "Vejiga"),
        measure("vejiga_residuo", "Residuo posmiccional (cc)", "Vejiga"),
    ],
)

ECO_PELVICA = echo_report(
    "ECO-PEL",
    "Informe ecográfico pélvico ginecológico",
    "Útero, endometrio, ovarios y fondo de saco por vía abdominal",
    """<h2>Vejiga</h2>
<p>{{ campo.vejiga }}.</p>

<h2>Útero</h2>
<table class="doc-grid">
<tr><td class="k">Posición</td><td>{{ campo.utero_posicion }}</td>
    <td class="k">Bordes</td><td>{{ campo.utero_bordes }}</td></tr>
<tr><td class="k">Medidas</td><td>{{ campo.utero_long }} × {{ campo.utero_ap }} × {{ campo.utero_transverso }} mm</td>
    <td class="k">Volumen</td><td>{{ campo.utero_volumen }} cc</td></tr>
<tr><td class="k">Miometrio</td><td>{{ campo.miometrio }}</td>
    <td class="k">Cavidad uterina</td><td>{{ campo.cavidad }}</td></tr>
<tr><td class="k">Endometrio</td><td colspan="3">{{ campo.endometrio }}, de {{ campo.endometrio_grosor }} mm de grosor</td></tr>
</table>

<h2>Anexos</h2>
<table class="doc-table">
<tr><th></th><th>Ovario derecho</th><th>Ovario izquierdo</th></tr>
<tr><td>Medidas</td><td>{{ campo.ovario_derecho }}</td><td>{{ campo.ovario_izquierdo }}</td></tr>
<tr><td>Volumen</td><td>{{ campo.od_volumen }} cc</td><td>{{ campo.oi_volumen }} cc</td></tr>
<tr><td>Masas o quistes</td><td>{{ campo.od_masas }}</td><td>{{ campo.oi_masas }}</td></tr>
</table>

<h2>Fondo de saco de Douglas</h2>
<p>{{ campo.douglas }}.</p>""",
    [
        choice("vejiga", "Vejiga", "Vejiga", opts("A repleción", "Poca repleción", "Vacua"), "A repleción"),
        choice("utero_posicion", "Posición", "Útero", opts("Anteversoflexo", "Retroversoflexo", "Intermedio"), "Anteversoflexo"),
        choice("utero_bordes", "Bordes", "Útero", opts("Regulares", "Irregulares"), "Regulares"),
        measure("utero_long", "Longitud (mm)", "Útero"),
        measure("utero_ap", "Anteroposterior (mm)", "Útero"),
        measure("utero_transverso", "Transverso (mm)", "Útero"),
        measure("utero_volumen", "Volumen (cc)", "Útero"),
        choice("miometrio", "Miometrio", "Útero", opts("Homogéneo", "Heterogéneo"), "Homogéneo"),
        choice("cavidad", "Cavidad uterina", "Útero", opts("Vacua", "Ocupada"), "Vacua"),
        choice("endometrio", "Endometrio · aspecto", "Útero", opts("Lineal", "Trilaminar", "Heterogéneo"), "Lineal"),
        measure("endometrio_grosor", "Endometrio · grosor (mm)", "Útero"),
        {"key": "ovario_derecho", "label": "Ovario derecho · medidas", "type": "text", "group": "Anexos", "placeholder": "30 × 20 × 18 mm"},
        measure("od_volumen", "Ovario derecho · volumen (cc)", "Anexos"),
        choice("od_masas", "Ovario derecho · masas o quistes", "Anexos", SI_NO, "No"),
        {"key": "ovario_izquierdo", "label": "Ovario izquierdo · medidas", "type": "text", "group": "Anexos", "placeholder": "30 × 20 × 18 mm"},
        measure("oi_volumen", "Ovario izquierdo · volumen (cc)", "Anexos"),
        choice("oi_masas", "Ovario izquierdo · masas o quistes", "Anexos", SI_NO, "No"),
        choice("douglas", "Fondo de saco de Douglas", "Douglas", opts("Libre", "Con líquido libre"), "Libre"),
    ],
)

ECO_HISTEROSONOGRAFIA = echo_report(
    "ECO-HIS",
    "Informe de histerosonografía",
    "Cavidad uterina evaluada con solución salina estéril",
    """<h2>Útero</h2>
<table class="doc-grid">
<tr><td class="k">FUR</td><td>{{ campo.fur }}</td>
    <td class="k">Posición</td><td>{{ campo.utero_posicion }}</td></tr>
<tr><td class="k">Medidas</td><td>{{ campo.utero_long }} × {{ campo.utero_ap }} × {{ campo.utero_transverso }} mm</td>
    <td class="k">Volumen</td><td>{{ campo.utero_volumen }} cc</td></tr>
<tr><td class="k">Miometrio</td><td>{{ campo.miometrio }}</td>
    <td class="k">Bordes</td><td>{{ campo.utero_bordes }}</td></tr>
<tr><td class="k">Endometrio</td><td>{{ campo.endometrio }}, de {{ campo.endometrio_grosor }} mm</td>
    <td class="k">Cérvix</td><td>{{ campo.cervix }}</td></tr>
</table>

<h2>Histerosonografía</h2>
<p>Tras la aplicación de solución hidrosalina estéril se evidencia:</p>
<table class="doc-grid">
<tr><td class="k">Distensibilidad de la cavidad</td><td>{{ campo.distensibilidad }}</td>
    <td class="k">Endometrio</td><td>{{ campo.endometrio_hs }}</td></tr>
<tr><td class="k">Adherencias</td><td>{{ campo.adherencias }}</td>
    <td class="k">Lesiones focales</td><td>{{ campo.lesiones }}</td></tr>
</table>

<h2>Anexos y fondo de saco</h2>
<table class="doc-grid">
<tr><td class="k">Ovario derecho</td><td>{{ campo.ovario_derecho }}</td>
    <td class="k">Ovario izquierdo</td><td>{{ campo.ovario_izquierdo }}</td></tr>
<tr><td class="k">Douglas</td><td colspan="3">{{ campo.douglas }}</td></tr>
</table>""",
    [
        {"key": "fur", "label": "Fecha de última regla", "type": "date", "group": "Útero"},
        choice("utero_posicion", "Posición", "Útero", opts("Anteversoflexo", "Retroversoflexo", "Intermedio"), "Anteversoflexo"),
        measure("utero_long", "Longitud (mm)", "Útero"),
        measure("utero_ap", "Anteroposterior (mm)", "Útero"),
        measure("utero_transverso", "Transverso (mm)", "Útero"),
        measure("utero_volumen", "Volumen (cc)", "Útero"),
        choice("miometrio", "Miometrio", "Útero", opts("Homogéneo", "Heterogéneo"), "Homogéneo"),
        choice("utero_bordes", "Bordes", "Útero", opts("Regulares", "Irregulares"), "Regulares"),
        choice("endometrio", "Endometrio · aspecto", "Útero", opts("Homogéneo", "Heterogéneo"), "Homogéneo"),
        measure("endometrio_grosor", "Endometrio · grosor (mm)", "Útero"),
        choice("cervix", "Cérvix", "Útero", opts("De aspecto normal", "Alterado"), "De aspecto normal"),
        choice("distensibilidad", "Distensibilidad de la cavidad", "Histerosonografía", opts("Normal", "Disminuida"), "Normal"),
        choice("endometrio_hs", "Endometrio tras la distensión", "Histerosonografía", opts("Normal", "Irregular"), "Normal"),
        choice("adherencias", "Adherencias", "Histerosonografía", opts("No impresionan", "Presentes"), "No impresionan"),
        {"key": "lesiones", "label": "Lesiones focales", "type": "text", "group": "Histerosonografía", "default": "No se evidencian", "wide": True},
        {"key": "ovario_derecho", "label": "Ovario derecho", "type": "text", "group": "Anexos", "placeholder": "30 × 20 mm, volumen 6 cc"},
        {"key": "ovario_izquierdo", "label": "Ovario izquierdo", "type": "text", "group": "Anexos", "placeholder": "30 × 20 mm, volumen 6 cc"},
        choice("douglas", "Fondo de saco de Douglas", "Anexos", opts("Libre, sin líquido", "Con líquido libre", "Obturado"), "Libre, sin líquido"),
    ],
)

ECO_PROSTATA = echo_report(
    "ECO-PRO",
    "Informe ecográfico de próstata",
    "Vejiga, próstata y residuo posmiccional",
    """<h2>Vejiga</h2>
<table class="doc-grid">
<tr><td class="k">Repleción</td><td>{{ campo.vejiga_replecion }}</td>
    <td class="k">Paredes</td><td>{{ campo.vejiga_paredes }}</td></tr>
<tr><td class="k">Contenido anecoico</td><td>{{ campo.vejiga_contenido }}</td>
    <td class="k">Imágenes expansivas</td><td>{{ campo.vejiga_expansivas }}</td></tr>
<tr><td class="k">Cálculos en su interior</td><td>{{ campo.vejiga_calculos }}</td>
    <td class="k">Volumen premiccional</td><td>{{ campo.vejiga_volumen }} cc</td></tr>
<tr><td class="k">Residuo posmiccional</td><td colspan="3">{{ campo.residuo }} cc</td></tr>
</table>

<h2>Próstata</h2>
<table class="doc-grid">
<tr><td class="k">Bordes</td><td>{{ campo.prostata_bordes }}</td>
    <td class="k">Ecoestructura</td><td>{{ campo.prostata_ecoestructura }}</td></tr>
<tr><td class="k">Medidas</td><td>{{ campo.prostata_transverso }} × {{ campo.prostata_ap }} × {{ campo.prostata_longitudinal }} mm</td>
    <td class="k">Volumen</td><td>{{ campo.prostata_volumen }} cc</td></tr>
</table>""",
    [
        choice("vejiga_replecion", "Repleción", "Vejiga", opts("Buena", "Poca", "Vacua"), "Buena"),
        choice("vejiga_paredes", "Paredes", "Vejiga", opts("Regulares y delgadas", "Engrosadas", "Irregulares"), "Regulares y delgadas"),
        choice("vejiga_contenido", "Contenido anecoico", "Vejiga", opts("Sí", "No"), "Sí"),
        choice("vejiga_expansivas", "Imágenes expansivas", "Vejiga", SI_NO, "No"),
        choice("vejiga_calculos", "Cálculos en su interior", "Vejiga", SI_NO, "No"),
        measure("vejiga_volumen", "Volumen premiccional (cc)", "Vejiga"),
        measure("residuo", "Residuo posmiccional (cc)", "Vejiga"),
        choice("prostata_bordes", "Bordes", "Próstata", opts("Regulares", "Irregulares"), "Regulares"),
        choice("prostata_ecoestructura", "Ecoestructura", "Próstata", opts("Homogénea", "Heterogénea"), "Homogénea"),
        measure("prostata_transverso", "Transverso (mm)", "Próstata"),
        measure("prostata_ap", "Anteroposterior (mm)", "Próstata"),
        measure("prostata_longitudinal", "Longitudinal (mm)", "Próstata"),
        measure("prostata_volumen", "Volumen (cc)", "Próstata"),
    ],
)

ECO_TESTICULAR = echo_report(
    "ECO-TES",
    "Informe ecográfico de testículos y escroto",
    "Ecoestructura, volumen testicular y contenido escrotal",
    """<h2>Testículos</h2>
<table class="doc-table">
<tr><th></th><th>Testículo derecho</th><th>Testículo izquierdo</th></tr>
<tr><td>Ecoestructura</td><td>{{ campo.td_ecoestructura }}</td><td>{{ campo.ti_ecoestructura }}</td></tr>
<tr><td>Medidas</td><td>{{ campo.td_largo }} × {{ campo.td_ancho }} × {{ campo.td_ap }} mm</td>
    <td>{{ campo.ti_largo }} × {{ campo.ti_ancho }} × {{ campo.ti_ap }} mm</td></tr>
<tr><td>Volumen</td><td>{{ campo.td_volumen }} cc</td><td>{{ campo.ti_volumen }} cc</td></tr>
<tr><td>Imágenes expansivas</td><td>{{ campo.td_expansivas }}</td><td>{{ campo.ti_expansivas }}</td></tr>
<tr><td>Epidídimo</td><td>{{ campo.td_epididimo }}</td><td>{{ campo.ti_epididimo }}</td></tr>
</table>

<h2>Escroto</h2>
<table class="doc-grid">
<tr><td class="k">Hidrocele</td><td>{{ campo.hidrocele }}</td>
    <td class="k">Varicocele</td><td>{{ campo.varicocele }}</td></tr>
<tr><td class="k">Descripción</td><td colspan="3">{{ campo.escroto }}</td></tr>
</table>""",
    [
        choice("td_ecoestructura", "Testículo derecho · ecoestructura", "Testículo derecho", opts("Homogénea", "Heterogénea"), "Homogénea"),
        measure("td_largo", "Largo (mm)", "Testículo derecho"),
        measure("td_ancho", "Ancho (mm)", "Testículo derecho"),
        measure("td_ap", "Anteroposterior (mm)", "Testículo derecho"),
        measure("td_volumen", "Volumen (cc)", "Testículo derecho"),
        choice("td_expansivas", "Imágenes expansivas", "Testículo derecho", SI_NO, "No"),
        choice("td_epididimo", "Epidídimo", "Testículo derecho", opts("De aspecto normal", "Alterado"), "De aspecto normal"),
        choice("ti_ecoestructura", "Testículo izquierdo · ecoestructura", "Testículo izquierdo", opts("Homogénea", "Heterogénea"), "Homogénea"),
        measure("ti_largo", "Largo (mm)", "Testículo izquierdo"),
        measure("ti_ancho", "Ancho (mm)", "Testículo izquierdo"),
        measure("ti_ap", "Anteroposterior (mm)", "Testículo izquierdo"),
        measure("ti_volumen", "Volumen (cc)", "Testículo izquierdo"),
        choice("ti_expansivas", "Imágenes expansivas", "Testículo izquierdo", SI_NO, "No"),
        choice("ti_epididimo", "Epidídimo", "Testículo izquierdo", opts("De aspecto normal", "Alterado"), "De aspecto normal"),
        choice("hidrocele", "Hidrocele", "Escroto", SI_NO, "No"),
        choice("varicocele", "Varicocele", "Escroto", SI_NO, "No"),
        {"key": "escroto", "label": "Descripción del escroto", "type": "text", "group": "Escroto", "default": "De aspecto normal", "wide": True},
    ],
)

ECO_PARTES_BLANDAS = echo_report(
    "ECO-PBL",
    "Informe ecográfico de partes blandas",
    "Piel, tejido celular subcutáneo y plano muscular",
    """<h2>Región evaluada</h2>
<p>{{ campo.region }}</p>

<h2>Hallazgos</h2>
<table class="doc-grid">
<tr><td class="k">Piel</td><td>{{ campo.piel }}</td>
    <td class="k">Tejido celular subcutáneo</td><td>{{ campo.tcs }}</td></tr>
<tr><td class="k">Tejido muscular</td><td>{{ campo.muscular }}</td>
    <td class="k">Colecciones</td><td>{{ campo.colecciones }}</td></tr>
<tr><td class="k">Lesión focal</td><td colspan="3">{{ campo.lesion }}</td></tr>
</table>""",
    [
        {"key": "region", "label": "Región evaluada", "type": "text", "group": "Región", "required": True, "wide": True,
         "placeholder": "Cara anterior de muslo derecho"},
        choice("piel", "Piel", "Hallazgos", opts("De aspecto normal", "Alterada"), "De aspecto normal"),
        choice("tcs", "Tejido celular subcutáneo", "Hallazgos", opts("De aspecto normal", "Alterado"), "De aspecto normal"),
        choice("muscular", "Tejido muscular", "Hallazgos", opts("De aspecto normal", "Alterado"), "De aspecto normal"),
        choice("colecciones", "Colecciones líquidas", "Hallazgos", SI_NO, "No"),
        {"key": "lesion", "label": "Lesión focal", "type": "text", "group": "Hallazgos", "default": "No se evidencia", "wide": True},
    ],
)

ECO_PERFIL_BIOFISICO = echo_report(
    "ECO-PBF",
    "Informe ecográfico de perfil biofísico fetal",
    "Biometría, placenta y los cuatro parámetros del perfil biofísico",
    """<h2>Evaluación fetal</h2>
<table class="doc-grid">
<tr><td class="k">Visualización</td><td>{{ campo.visualizacion }}</td>
    <td class="k">Situación y presentación</td><td>{{ campo.situacion }}</td></tr>
<tr><td class="k">Latido cardíaco fetal</td><td colspan="3">{{ campo.lcf }} lpm</td></tr>
</table>

"""
    + FETAL_BIOMETRY_BLOCK
    + """

"""
    + FETAL_ANNEX_BLOCK
    + """

<h2>Perfil biofísico</h2>
<table class="doc-table">
<tr><th>Parámetro</th><th>Puntaje</th><th>Parámetro</th><th>Puntaje</th></tr>
<tr><td>Movimientos fetales</td><td>{{ campo.movimientos }}</td>
    <td>Reactividad fetal</td><td>{{ campo.reactividad }}</td></tr>
<tr><td>Movimientos respiratorios</td><td>{{ campo.respiratorios }}</td>
    <td>Tono fetal</td><td>{{ campo.tono }}</td></tr>
<tr><td><strong>Perfil biofísico fetal</strong></td>
    <td colspan="3"><strong>{{ campo.puntaje }}/8</strong></td></tr>
</table>
<p class="doc-note">Cada parámetro puntúa 0 (ausente) o 2 (presente). Un perfil de 8/8
corresponde a un feto sin signos de compromiso del bienestar.</p>""",
    [
        choice("visualizacion", "Visualización", "Evaluación fetal", opts("Adecuada", "Limitada"), "Adecuada"),
        {"key": "situacion", "label": "Situación y presentación", "type": "text", "group": "Evaluación fetal", "placeholder": "Longitudinal cefálico, dorso izquierdo"},
        measure("lcf", "Latido cardíaco fetal (lpm)", "Evaluación fetal"),
        *fetal_biometry_fields(),
        *fetal_annex_fields(),
        *[
            {
                "key": key,
                "label": label,
                "type": "select",
                "group": "Perfil biofísico",
                "options": BIOPHYSICAL_OPTIONS,
                "default": "2",
            }
            for key, label in (
                ("movimientos", "Movimientos fetales"),
                ("reactividad", "Reactividad fetal"),
                ("respiratorios", "Movimientos respiratorios"),
                ("tono", "Tono fetal"),
            )
        ],
        {
            "key": "puntaje",
            "label": "Perfil biofísico (sobre 8)",
            "type": "computed",
            "group": "Perfil biofísico",
            "sum": ["movimientos", "reactividad", "respiratorios", "tono"],
            "help": "Se calcula solo a partir de los cuatro parámetros anteriores.",
        },
    ],
)

ECO_DOPPLER = echo_report(
    "ECO-DOP",
    "Informe ecográfico Doppler materno fetal",
    "Biometría e índices de pulsatilidad umbilical, cerebral y uterinos",
    """<h2>Evaluación fetal</h2>
<table class="doc-grid">
<tr><td class="k">Visualización</td><td>{{ campo.visualizacion }}</td>
    <td class="k">Situación y presentación</td><td>{{ campo.situacion }}</td></tr>
<tr><td class="k">Latido cardíaco fetal</td><td colspan="3">{{ campo.lcf }} lpm</td></tr>
</table>

"""
    + FETAL_BIOMETRY_BLOCK
    + """

"""
    + FETAL_ANNEX_BLOCK
    + """

<h2>Índices de pulsatilidad</h2>
<table class="doc-table">
<tr><th>Vaso</th><th>IP</th><th>Percentil</th><th>Referencia</th></tr>
<tr><td>Arteria umbilical</td><td>{{ campo.aumb_ip }}</td><td>{{ campo.aumb_pc }}</td><td>&lt; P95</td></tr>
<tr><td>Arteria cerebral media</td><td>{{ campo.acm_ip }}</td><td>{{ campo.acm_pc }}</td><td>&gt; P5</td></tr>
<tr><td>Arterias uterinas</td>
    <td>Der. {{ campo.aut_der_ip }} · Izq. {{ campo.aut_izq_ip }}</td>
    <td>{{ campo.aut_pc }}</td><td>&lt; P95</td></tr>
<tr><td>Relación cerebro-placentaria</td><td>{{ campo.rcp }}</td><td colspan="2">&gt; P5</td></tr>
</table>""",
    [
        choice("visualizacion", "Visualización", "Evaluación fetal", opts("Adecuada", "Limitada"), "Adecuada"),
        {"key": "situacion", "label": "Situación y presentación", "type": "text", "group": "Evaluación fetal", "placeholder": "Longitudinal cefálico, dorso izquierdo"},
        measure("lcf", "Latido cardíaco fetal (lpm)", "Evaluación fetal"),
        *fetal_biometry_fields(),
        *fetal_annex_fields(),
        measure("aumb_ip", "Arteria umbilical · IP", "Doppler"),
        {"key": "aumb_pc", "label": "Arteria umbilical · percentil", "type": "text", "group": "Doppler", "placeholder": "< P95"},
        measure("acm_ip", "Arteria cerebral media · IP", "Doppler"),
        {"key": "acm_pc", "label": "Arteria cerebral media · percentil", "type": "text", "group": "Doppler", "placeholder": "> P5"},
        measure("aut_der_ip", "Arteria uterina derecha · IP", "Doppler"),
        measure("aut_izq_ip", "Arteria uterina izquierda · IP", "Doppler"),
        {"key": "aut_pc", "label": "Arterias uterinas · percentil", "type": "text", "group": "Doppler", "placeholder": "< P95"},
        measure("rcp", "Relación cerebro-placentaria", "Doppler"),
    ],
)

ECO_GEMELAR = echo_report(
    "ECO-GEM",
    "Informe ecográfico obstétrico gemelar",
    "Biometría, discordancia y Doppler de ambos fetos",
    """<h2>Evaluación fetal</h2>
<table class="doc-grid">
<tr><td class="k">Visualización</td><td>{{ campo.visualizacion }}</td>
    <td class="k">Número de fetos</td><td>{{ campo.numero_fetos }}</td></tr>
<tr><td class="k">Corionicidad y amnionicidad</td><td colspan="3">{{ campo.corionicidad }}</td></tr>
</table>

<h2>Biometría</h2>
<table class="doc-table">
<tr><th></th><th>Feto 1</th><th>Feto 2</th></tr>
<tr><td>Situación y presentación</td><td>{{ campo.f1_presentacion }}</td><td>{{ campo.f2_presentacion }}</td></tr>
<tr><td>DBP</td><td>{{ campo.f1_dbp }} mm</td><td>{{ campo.f2_dbp }} mm</td></tr>
<tr><td>CC</td><td>{{ campo.f1_cc }} mm</td><td>{{ campo.f2_cc }} mm</td></tr>
<tr><td>CA</td><td>{{ campo.f1_ca }} mm</td><td>{{ campo.f2_ca }} mm</td></tr>
<tr><td>LF</td><td>{{ campo.f1_lf }} mm</td><td>{{ campo.f2_lf }} mm</td></tr>
<tr><td>LCF</td><td>{{ campo.f1_lcf }} lpm</td><td>{{ campo.f2_lcf }} lpm</td></tr>
<tr><td>Ponderado</td><td>{{ campo.f1_peso }} g &nbsp;±&nbsp; {{ campo.f1_peso_error }} g</td>
    <td>{{ campo.f2_peso }} g &nbsp;±&nbsp; {{ campo.f2_peso_error }} g</td></tr>
<tr><td>Percentil</td><td>{{ campo.f1_percentil }} %</td><td>{{ campo.f2_percentil }} %</td></tr>
<tr><td>Pozo mayor de líquido</td><td>{{ campo.f1_pozo }} mm</td><td>{{ campo.f2_pozo }} mm</td></tr>
</table>
<table class="doc-grid">
<tr><td class="k">Discordancia fetal</td><td>{{ campo.discordancia }} %</td>
    <td class="k">Edad gestacional</td><td>{{ campo.edad_gestacional }}</td></tr>
<tr><td class="k">Placenta</td><td>{{ campo.placenta }}</td>
    <td class="k">Grado</td><td>{{ campo.placenta_grado }}</td></tr>
</table>

<h2>Doppler fetal</h2>
<table class="doc-table">
<tr><th></th><th>Feto 1</th><th>Feto 2</th><th>Referencia</th></tr>
<tr><td>Arteria umbilical · IP</td><td>{{ campo.f1_aumb }}</td><td>{{ campo.f2_aumb }}</td><td>&lt; P95</td></tr>
<tr><td>Arteria cerebral media · IP</td><td>{{ campo.f1_acm }}</td><td>{{ campo.f2_acm }}</td><td>&gt; P5</td></tr>
</table>""",
    [
        choice("visualizacion", "Visualización", "Evaluación fetal", opts("Adecuada", "Limitada"), "Adecuada"),
        measure("numero_fetos", "Número de fetos", "Evaluación fetal", "2"),
        {"key": "corionicidad", "label": "Corionicidad y amnionicidad", "type": "text", "group": "Evaluación fetal", "wide": True,
         "placeholder": "Monocoriónica biamniótica"},
        {"key": "f1_presentacion", "label": "Feto 1 · situación y presentación", "type": "text", "group": "Feto 1"},
        measure("f1_dbp", "Feto 1 · DBP (mm)", "Feto 1"),
        measure("f1_cc", "Feto 1 · CC (mm)", "Feto 1"),
        measure("f1_ca", "Feto 1 · CA (mm)", "Feto 1"),
        measure("f1_lf", "Feto 1 · LF (mm)", "Feto 1"),
        measure("f1_lcf", "Feto 1 · LCF (lpm)", "Feto 1"),
        measure("f1_peso", "Feto 1 · ponderado (g)", "Feto 1"),
        measure("f1_peso_error", "Feto 1 · margen (g)", "Feto 1"),
        measure("f1_percentil", "Feto 1 · percentil (%)", "Feto 1"),
        measure("f1_pozo", "Feto 1 · pozo mayor (mm)", "Feto 1"),
        measure("f1_aumb", "Feto 1 · arteria umbilical IP", "Feto 1"),
        measure("f1_acm", "Feto 1 · arteria cerebral media IP", "Feto 1"),
        {"key": "f2_presentacion", "label": "Feto 2 · situación y presentación", "type": "text", "group": "Feto 2"},
        measure("f2_dbp", "Feto 2 · DBP (mm)", "Feto 2"),
        measure("f2_cc", "Feto 2 · CC (mm)", "Feto 2"),
        measure("f2_ca", "Feto 2 · CA (mm)", "Feto 2"),
        measure("f2_lf", "Feto 2 · LF (mm)", "Feto 2"),
        measure("f2_lcf", "Feto 2 · LCF (lpm)", "Feto 2"),
        measure("f2_peso", "Feto 2 · ponderado (g)", "Feto 2"),
        measure("f2_peso_error", "Feto 2 · margen (g)", "Feto 2"),
        measure("f2_percentil", "Feto 2 · percentil (%)", "Feto 2"),
        measure("f2_pozo", "Feto 2 · pozo mayor (mm)", "Feto 2"),
        measure("f2_aumb", "Feto 2 · arteria umbilical IP", "Feto 2"),
        measure("f2_acm", "Feto 2 · arteria cerebral media IP", "Feto 2"),
        measure("discordancia", "Discordancia fetal (%)", "Gestación"),
        {"key": "edad_gestacional", "label": "Edad gestacional por ecografía", "type": "text", "group": "Gestación", "placeholder": "32 semanas 4 días", "wide": True},
        {"key": "placenta", "label": "Placenta · localización", "type": "text", "group": "Gestación", "placeholder": "Fúndica posterior"},
        choice("placenta_grado", "Placenta · grado", "Gestación", opts("0", "I", "II", "III"), "II"),
    ],
)

ECO_MORFOLOGICA = echo_report(
    "ECO-MOR",
    "Informe ecográfico morfológico fetal",
    "Biometría y revisión estructura por estructura del feto",
    """<h2>Evaluación fetal</h2>
<table class="doc-grid">
<tr><td class="k">Visualización</td><td>{{ campo.visualizacion }}</td>
    <td class="k">Latido cardíaco fetal</td><td>{{ campo.lcf }} lpm</td></tr>
<tr><td class="k">Situación y presentación</td><td>{{ campo.situacion }}</td>
    <td class="k">Sexo fetal</td><td>{{ campo.sexo }}</td></tr>
</table>

"""
    + FETAL_BIOMETRY_BLOCK
    + """

"""
    + FETAL_ANNEX_BLOCK
    + """

<h2>Morfología fetal</h2>
<table class="doc-table">
<tr><th>Estructura</th><th>Hallazgo</th><th>Estructura</th><th>Hallazgo</th></tr>
<tr><td>Cabeza</td><td>{{ campo.cabeza }}</td><td>Complejo anterior</td><td>{{ campo.complejo_anterior }}</td></tr>
<tr><td>Cerebelo</td><td>{{ campo.cerebelo }} mm</td><td>Tálamos</td><td>{{ campo.talamos }}</td></tr>
<tr><td>Atrio</td><td>{{ campo.atrio }} mm</td><td>Fosa posterior</td><td>{{ campo.fosa_posterior }}</td></tr>
<tr><td>Cisterna magna</td><td>{{ campo.cisterna_magna }} mm</td><td>Línea media</td><td>{{ campo.linea_media }}</td></tr>
<tr><td>Cara · perfil</td><td>{{ campo.cara_perfil }}</td><td>Cara · labio</td><td>{{ campo.cara_labio }}</td></tr>
<tr><td>Corazón · 4 cámaras</td><td>{{ campo.corazon_camaras }}</td><td>Corazón · tractos de salida</td><td>{{ campo.corazon_tractos }}</td></tr>
<tr><td>Corazón · 3VT</td><td>{{ campo.corazon_3vt }}</td><td>Tórax</td><td>{{ campo.torax }}</td></tr>
<tr><td>Pulmones</td><td>{{ campo.pulmones }}</td><td>Diafragma</td><td>{{ campo.diafragma }}</td></tr>
<tr><td>Abdomen</td><td>{{ campo.abdomen }}</td><td>Pared abdominal e inserción del cordón</td><td>{{ campo.pared_abdominal }}</td></tr>
<tr><td>Cavidad gástrica</td><td>{{ campo.camara_gastrica }}</td><td>Vejiga</td><td>{{ campo.vejiga_fetal }}</td></tr>
<tr><td>Pelvis renal</td><td>{{ campo.pelvis_renal }}</td><td>Columna</td><td>{{ campo.columna }}</td></tr>
<tr><td>Extremidades</td><td colspan="3">{{ campo.extremidades }}</td></tr>
</table>
<p><strong>Longitud cervical:</strong> {{ campo.longitud_cervical }} mm</p>""",
    [
        choice("visualizacion", "Visualización", "Evaluación fetal", opts("Adecuada", "Limitada"), "Adecuada"),
        measure("lcf", "Latido cardíaco fetal (lpm)", "Evaluación fetal"),
        {"key": "situacion", "label": "Situación y presentación", "type": "text", "group": "Evaluación fetal", "placeholder": "Longitudinal cefálico, dorso izquierdo"},
        choice("sexo", "Sexo fetal", "Evaluación fetal", opts("Masculino", "Femenino", "No determinado"), "No determinado"),
        *fetal_biometry_fields(),
        *fetal_annex_fields(),
        *[
            choice(key, label, "Morfología", NORMAL_ALTERADO, "Aspecto normal")
            for key, label in (
                ("cabeza", "Cabeza"),
                ("complejo_anterior", "Complejo anterior"),
                ("talamos", "Tálamos"),
                ("fosa_posterior", "Fosa posterior"),
                ("linea_media", "Línea media"),
                ("cara_perfil", "Cara · perfil"),
                ("cara_labio", "Cara · labio"),
                ("corazon_camaras", "Corazón · 4 cámaras"),
                ("corazon_tractos", "Corazón · tractos de salida"),
                ("corazon_3vt", "Corazón · 3 vasos y tráquea"),
                ("torax", "Tórax"),
                ("pulmones", "Pulmones"),
                ("diafragma", "Diafragma"),
                ("abdomen", "Abdomen"),
                ("pared_abdominal", "Pared abdominal e inserción del cordón"),
                ("vejiga_fetal", "Vejiga"),
                ("pelvis_renal", "Pelvis renal"),
                ("columna", "Columna"),
            )
        ],
        measure("cerebelo", "Cerebelo (mm)", "Morfología"),
        measure("atrio", "Atrio (mm)", "Morfología"),
        measure("cisterna_magna", "Cisterna magna (mm)", "Morfología"),
        choice("camara_gastrica", "Cavidad gástrica", "Morfología", opts("Presente", "No visualizada"), "Presente"),
        {"key": "extremidades", "label": "Extremidades", "type": "text", "group": "Morfología", "wide": True,
         "default": "Brazos, manos, piernas y pies de aspecto normal"},
        measure("longitud_cervical", "Longitud cervical (mm)", "Cérvix"),
    ],
)

ECG = {
    "code": "ECG",
    "version": 1,
    "family": INFORME,
    "title": "Informe de electrocardiograma",
    "description": "Ritmo, frecuencia, ejes, intervalos y conclusión",
    "study_type": "OTRO",
    "requires_signature": True,
    "fields": [
        choice("ritmo", "Ritmo", "Trazado", opts("Sinusal", "No sinusal"), "Sinusal"),
        measure("frecuencia", "Frecuencia cardíaca (lpm)", "Trazado"),
        measure("eje", "Eje cardíaco (grados)", "Trazado"),
        {"key": "pr", "label": "Intervalo PR (seg)", "type": "text", "group": "Intervalos", "default": "0,15"},
        {"key": "qtc", "label": "QT corregido (ms)", "type": "text", "group": "Intervalos", "default": "400"},
        choice("st", "Segmento ST", "Intervalos", opts("Isoeléctrico, sin alteraciones significativas", "Con alteraciones"), "Isoeléctrico, sin alteraciones significativas"),
        choice("onda_q", "Onda Q patológica", "Intervalos", SI_NO, "No"),
        {"key": "descripcion", "label": "Descripción del trazado", "type": "textarea", "group": "Trazado", "wide": True,
         "default": "Onda P positiva en todas las derivaciones excepto en aVR, seguida de QRS estrecho. Onda T positiva en todas las derivaciones excepto en aVR."},
        FIELD_CONCLUSION,
    ],
    "body": (
        HEADER_CLINICAL
        + """<h2>Trazado</h2>
<table class="doc-grid">
<tr><td class="k">Ritmo</td><td>{{ campo.ritmo }}</td>
    <td class="k">Frecuencia</td><td>{{ campo.frecuencia }} lpm</td></tr>
<tr><td class="k">Eje cardíaco</td><td>{{ campo.eje }}°</td>
    <td class="k">Intervalo PR</td><td>{{ campo.pr }} seg</td></tr>
<tr><td class="k">QT corregido</td><td>{{ campo.qtc }} ms</td>
    <td class="k">Onda Q patológica</td><td>{{ campo.onda_q }}</td></tr>
<tr><td class="k">Segmento ST</td><td colspan="3">{{ campo.st }}</td></tr>
</table>
<p>{{ campo.descripcion|parrafos }}</p>
<h2>Conclusión</h2>
<p>{{ campo.conclusion|parrafos }}</p>"""
        + SIGN_DOCTOR
    ),
}


# Informes de laboratorio --------------------------------------------------
# Las hojas de resultados de la carpeta `Laboratorio` son todas el mismo
# formato: identificación, muestra, tabla de analitos con su valor de
# referencia y firma del responsable. Se declaran con `lab_report` para no
# repetir ese armazón en cada examen y, sobre todo, para que un mismo analito
# guarde siempre la misma clave: así la glucosa de un perfil bioquímico y la
# de un perfil renal son comparables entre sí.


class Analyte(NamedTuple):
    """Fila de la tabla de resultados: qué se mide, en qué unidad y su rango.

    El rango es texto de la hoja impresa, no una validación: un valor fuera de
    rango se registra igual, porque el informe debe poder reportar lo anormal.
    """

    key: str
    label: str
    unit: str = ""
    reference: str = ""
    type: str = "number"
    options: list[dict[str, str]] | None = None
    default: str | None = None


LAB_HEADER = """<table class="doc-grid">
<tr><td class="k">Paciente</td><td>{{ paciente.nombre_completo }}</td>
    <td class="k">Historia</td><td>{{ paciente.historia }}</td></tr>
<tr><td class="k">Documento</td><td>{{ paciente.tipo_documento }} {{ paciente.documento }}</td>
    <td class="k">Edad</td><td>{{ paciente.edad }}</td></tr>
<tr><td class="k">Fecha</td><td>{{ fecha.hoy }}</td>
    <td class="k">Hora</td><td>{{ fecha.hora }}</td></tr>
<tr><td class="k">Muestra</td><td>__MUESTRA__</td>
    <td class="k">Solicitado por</td><td>{{ campo.solicitante }}</td></tr>
</table>"""

LAB_SIGN = """<div class="doc-signatures">
<div class="sign"><div class="line"></div>
<div class="role">Responsable del laboratorio</div>
<div class="hint">{{ profesional.nombre }} · Colegiatura {{ profesional.cmp }}</div></div>
</div>"""

LAB_NOTE = (
    '<p class="doc-note">El resultado corresponde únicamente a la muestra recibida '
    "y debe interpretarse junto con la evaluación clínica del paciente.</p>"
)

FIELD_SOLICITANTE: dict[str, Any] = {
    "key": "solicitante",
    "label": "Médico que solicita",
    "type": "text",
    "group": "Muestra",
    "wide": True,
}

FIELD_OBSERVACIONES_LAB: dict[str, Any] = {
    "key": "observaciones",
    "label": "Observaciones",
    "type": "textarea",
    "group": "Observaciones",
    "default": "Ninguna",
    "wide": True,
}


def _analyte_field(item: Analyte, group: str) -> dict[str, Any]:
    field: dict[str, Any] = {
        "key": item.key,
        "label": f"{item.label} ({item.unit})" if item.unit else item.label,
        "type": "select" if item.options else item.type,
        "group": group,
    }
    if item.options:
        field["options"] = item.options
    if item.default is not None:
        field["default"] = item.default
    if item.reference:
        field["help"] = f"Referencia: {item.reference}"
    return field


def _analyte_row(item: Analyte) -> str:
    value = "{{ campo." + item.key + " }}" + (f" {item.unit}" if item.unit else "")
    return f"<tr><td>{item.label}</td><td>{value}</td><td>{item.reference}</td></tr>"


def lab_report(
    code: str,
    title: str,
    description: str,
    sample: str,
    sections: tuple[tuple[str, tuple[Analyte, ...]], ...],
) -> dict[str, Any]:
    """Informe de laboratorio: muestra, analitos, observaciones y firma."""
    fields: list[dict[str, Any]] = [FIELD_SOLICITANTE]
    blocks: list[str] = []

    for group, analytes in sections:
        fields.extend(_analyte_field(item, group) for item in analytes)
        blocks.append(
            f"<h2>{group}</h2>"
            '<table class="doc-table">'
            "<tr><th>Analito</th><th>Resultado</th><th>Valores de referencia</th></tr>"
            + "".join(_analyte_row(item) for item in analytes)
            + "</table>"
        )

    fields.append(FIELD_OBSERVACIONES_LAB)
    return {
        "code": code,
        "version": 1,
        "family": INFORME,
        "title": title,
        "description": description,
        "study_type": "LABORATORIO",
        "requires_signature": True,
        "fields": fields,
        "body": (
            LAB_HEADER.replace("__MUESTRA__", sample)
            + "".join(blocks)
            + "<h2>Observaciones</h2><p>{{ campo.observaciones|parrafos }}</p>"
            + LAB_SIGN
            + LAB_NOTE
        ),
    }


NO_SE_OBSERVA = opts("No se observa", "Escasos", "Regular cantidad", "Abundantes")
NO_REACTIVO = opts("No reactivo", "Reactivo")

LAB_HEMOGRAMA = lab_report(
    "LAB-HEM",
    "Hemograma completo",
    "Serie roja, plaquetas y fórmula leucocitaria",
    "Sangre total con EDTA",
    (
        ("Serie roja y plaquetas", (
            Analyte("hematocrito", "Hematocrito", "%", "Varones 40 a 54 · Mujeres 36 a 47"),
            Analyte("hemoglobina", "Hemoglobina", "g/dL", "Varones 13 a 17 · Mujeres 12 a 16"),
            Analyte("plaquetas", "Recuento de plaquetas", "por mm³", "150 000 a 450 000"),
            Analyte("vcm", "Volumen corpuscular medio", "fL", "80 a 100"),
            Analyte("hcm", "Hemoglobina corpuscular media", "pg", "27 a 32"),
            Analyte("chcm", "Concentración corpuscular media", "g/dL", "32 a 36"),
        )),
        ("Serie blanca", (
            Analyte("leucocitos", "Leucocitos", "por mm³", "5 000 a 10 000"),
            Analyte("abastonados", "Abastonados", "%", "0 a 1"),
            Analyte("segmentados", "Segmentados", "%", "60 a 75"),
            Analyte("eosinofilos", "Eosinófilos", "%", "0,5 a 4"),
            Analyte("basofilos", "Basófilos", "%", "0,5 a 1"),
            Analyte("monocitos", "Monocitos", "%", "3 a 8"),
            Analyte("linfocitos", "Linfocitos", "%", "20 a 35"),
        )),
    ),
)

LAB_ORINA = lab_report(
    "LAB-ORI",
    "Examen completo de orina",
    "Examen macroscópico, reacción bioquímica y sedimento urinario",
    "Orina de primer chorro medio",
    (
        ("Examen macroscópico", (
            Analyte("color", "Color", type="select",
                    options=opts("Amarillo", "Amarillo claro", "Amarillo ámbar", "Rojizo", "Incoloro"),
                    default="Amarillo"),
            Analyte("aspecto", "Aspecto", type="select",
                    options=opts("Transparente", "Ligeramente turbio", "Turbio"),
                    default="Transparente"),
            Analyte("ph", "pH", "", "4,5 a 8,0"),
            Analyte("densidad", "Densidad", "", "1,005 a 1,030"),
        )),
        ("Reacción bioquímica", (
            Analyte("glucosa", "Glucosa", type="select", options=NEGATIVO_POSITIVO, default="Negativo", reference="Negativo"),
            Analyte("proteinas", "Proteínas", type="select", options=NEGATIVO_POSITIVO, default="Negativo", reference="Negativo"),
            Analyte("bilirrubina", "Bilirrubina", type="select", options=NEGATIVO_POSITIVO, default="Negativo", reference="Negativo"),
            Analyte("urobilinogeno", "Urobilinógeno", type="select", options=NEGATIVO_POSITIVO, default="Negativo", reference="Normal"),
            Analyte("hemoglobina_orina", "Hemoglobina", type="select", options=NEGATIVO_POSITIVO, default="Negativo", reference="Negativo"),
            Analyte("nitritos", "Nitritos", type="select", options=NEGATIVO_POSITIVO, default="Negativo", reference="Negativo"),
            Analyte("cetonas", "Cetonas", type="select", options=NEGATIVO_POSITIVO, default="Negativo", reference="Negativo"),
            Analyte("ascorbico", "Ácido ascórbico", type="select", options=NEGATIVO_POSITIVO, default="Negativo", reference="Negativo"),
        )),
        ("Sedimento urinario", (
            Analyte("celulas_epiteliales", "Células epiteliales", "por campo", "0 a 3", type="text"),
            Analyte("hematies", "Hematíes", "por campo", "0 a 2", type="text"),
            Analyte("leucocitos_orina", "Leucocitos", "por campo", "0 a 5", type="text"),
            Analyte("piocitos", "Piocitos", type="select", options=NO_SE_OBSERVA, default="No se observa", reference="No se observa"),
            Analyte("germenes", "Gérmenes", type="select", options=NO_SE_OBSERVA, default="No se observa", reference="No se observa"),
            Analyte("cristales", "Cristales", type="text", reference="No se observa"),
            Analyte("cilindros", "Cilindros", type="text", reference="No se observa"),
            Analyte("levaduras", "Levaduras", type="select", options=NO_SE_OBSERVA, default="No se observa", reference="No se observa"),
            Analyte("filamento_mucoide", "Filamento mucoide", type="select", options=NO_SE_OBSERVA, default="No se observa", reference="Escaso"),
        )),
    ),
)

LAB_PARASITOLOGICO = lab_report(
    "LAB-PAR",
    "Examen parasitológico de heces",
    "Examen macroscópico y microscópico, simple o seriado",
    "Heces",
    (
        ("Examen macroscópico", (
            Analyte("color_heces", "Color", type="text"),
            Analyte("consistencia", "Consistencia", type="select",
                    options=opts("Formada", "Semiformada", "Blanda", "Líquida"), default="Formada"),
            Analyte("moco", "Moco", type="select", options=AUSENTE_PRESENTE, default="Ausente", reference="Ausente"),
            Analyte("sangre_macro", "Sangre visible", type="select", options=AUSENTE_PRESENTE, default="Ausente", reference="Ausente"),
        )),
        ("Examen microscópico", (
            Analyte("quistes", "Quistes", type="text", reference="No se observa"),
            Analyte("trofozoitos", "Trofozoítos", type="text", reference="No se observa"),
            Analyte("huevos", "Huevos de helmintos", type="text", reference="No se observa"),
            Analyte("larvas", "Larvas", type="text", reference="No se observa"),
            Analyte("leucocitos_heces", "Leucocitos", "por campo", "0 a 2", type="text"),
            Analyte("hematies_heces", "Hematíes", "por campo", "No se observa", type="text"),
            Analyte("levaduras_heces", "Levaduras", type="select", options=NO_SE_OBSERVA, default="No se observa", reference="Escasas"),
            Analyte("restos", "Restos alimenticios", type="select", options=NO_SE_OBSERVA, default="Escasos"),
        )),
    ),
)

LAB_BIOQUIMICA = lab_report(
    "LAB-BIO",
    "Perfil bioquímico",
    "Glucosa, urea, creatinina y ácido úrico",
    "Suero",
    (
        ("Bioquímica", (
            Analyte("glucosa_serica", "Glucosa", "mg/dL", "70 a 110"),
            Analyte("urea", "Urea", "mg/dL", "10 a 50"),
            Analyte("creatinina", "Creatinina", "mg/dL", "0,6 a 1,2"),
            Analyte("acido_urico", "Ácido úrico", "mg/dL", "Varones 3,4 a 7,0 · Mujeres 2,4 a 5,7"),
        )),
    ),
)

LAB_LIPIDICO = lab_report(
    "LAB-LIP",
    "Perfil lipídico",
    "Colesterol total, triglicéridos, HDL y LDL",
    "Suero en ayunas de 12 horas",
    (
        ("Perfil lipídico", (
            Analyte("colesterol_total", "Colesterol total", "mg/dL", "140 a 200"),
            Analyte("trigliceridos", "Triglicéridos", "mg/dL", "25 a 160"),
            Analyte("hdl", "Colesterol HDL", "mg/dL", "30 a 70"),
            Analyte("ldl", "Colesterol LDL", "mg/dL", "Hasta 150"),
            Analyte("vldl", "Colesterol VLDL", "mg/dL", "5 a 40"),
            Analyte("glucosa_lipidos", "Glucosa", "mg/dL", "70 a 110"),
        )),
    ),
)

LAB_HEPATICO = lab_report(
    "LAB-HEP",
    "Perfil hepático",
    "Transaminasas, bilirrubinas, fosfatasa alcalina y proteínas",
    "Suero",
    (
        ("Enzimas", (
            Analyte("tgo", "TGO (AST)", "U/L", "Hasta 40"),
            Analyte("tgp", "TGP (ALT)", "U/L", "Hasta 41"),
            Analyte("fosfatasa_alcalina", "Fosfatasa alcalina", "U/L", "40 a 129"),
            Analyte("ggt", "Gamma glutamil transpeptidasa", "U/L", "8 a 61"),
        )),
        ("Bilirrubinas", (
            Analyte("bilirrubina_total", "Bilirrubina total", "mg/dL", "0,2 a 1,2"),
            Analyte("bilirrubina_directa", "Bilirrubina directa", "mg/dL", "0,0 a 0,3"),
            Analyte("bilirrubina_indirecta", "Bilirrubina indirecta", "mg/dL", "0,2 a 0,9"),
        )),
        ("Proteínas", (
            Analyte("proteinas_totales", "Proteínas totales", "g/dL", "6,4 a 8,3"),
            Analyte("albumina", "Albúmina", "g/dL", "3,5 a 5,2"),
            Analyte("globulinas", "Globulinas", "g/dL", "2,0 a 3,5"),
        )),
    ),
)

LAB_RENAL = lab_report(
    "LAB-REN",
    "Perfil renal",
    "Urea, creatinina, depuración y proteínas en orina de 24 horas",
    "Suero y orina de 24 horas",
    (
        ("Suero", (
            Analyte("urea_renal", "Urea", "mg/dL", "10 a 50"),
            Analyte("creatinina_renal", "Creatinina", "mg/dL", "0,6 a 1,2"),
            Analyte("acido_urico_renal", "Ácido úrico", "mg/dL", "2,4 a 7,0"),
        )),
        ("Orina de 24 horas", (
            Analyte("volumen_24h", "Volumen urinario", "mL", "800 a 2 000"),
            Analyte("depuracion", "Depuración de creatinina", "mL/min", "88 a 137"),
            Analyte("proteinas_24h", "Proteínas totales", "mg/24 h", "Hasta 150"),
        )),
    ),
)

LAB_TIROIDEO = lab_report(
    "LAB-TIR",
    "Perfil tiroideo",
    "TSH, T3 y T4 libre por IEMA / ELISA",
    "Suero",
    (
        ("Hormonas tiroideas", (
            Analyte("tsh", "TSH", "µUI/mL", "0,28 a 5,60"),
            Analyte("t3", "T3", "ng/mL", "0,80 a 2,00"),
            Analyte("t4_libre", "T4 libre", "ng/dL", "0,93 a 1,70"),
        )),
    ),
)

LAB_GLICOSILADA = lab_report(
    "LAB-GLI",
    "Hemoglobina glicosilada",
    "HbA1c y glucosa promedio estimada",
    "Sangre total con EDTA",
    (
        ("Control metabólico", (
            Analyte("hba1c", "Hemoglobina glicosilada A1c", "%",
                    "Normal menos de 5,7 · Prediabetes 5,7 a 6,4 · Diabetes 6,5 a más"),
            Analyte("glucosa_promedio", "Glucosa promedio estimada", "mg/dL", "Hasta 117"),
        )),
    ),
)

LAB_GRUPO = lab_report(
    "LAB-GRU",
    "Grupo sanguíneo y factor Rh",
    "Inmunohematología: grupo ABO y factor Rh",
    "Sangre total",
    (
        ("Inmunohematología", (
            Analyte("grupo", "Grupo sanguíneo", type="select", options=opts("O", "A", "B", "AB")),
            Analyte("factor", "Factor Rh", type="select", options=opts("Positivo", "Negativo")),
        )),
    ),
)

LAB_COAGULACION = lab_report(
    "LAB-COA",
    "Tiempos de coagulación",
    "Coagulación, sangría, protrombina, INR y TTPa",
    "Sangre total y plasma citratado",
    (
        ("Hemostasia", (
            Analyte("tiempo_coagulacion", "Tiempo de coagulación", "minutos", "5 a 10"),
            Analyte("tiempo_sangria", "Tiempo de sangría", "minutos", "1 a 3"),
            Analyte("tiempo_protrombina", "Tiempo de protrombina", "segundos", "11 a 15"),
            Analyte("inr", "INR", "", "0,8 a 1,2"),
            Analyte("ttpa", "Tiempo de tromboplastina parcial", "segundos", "25 a 35"),
        )),
    ),
)

LAB_VSG = lab_report(
    "LAB-VSG",
    "Velocidad de sedimentación globular",
    "VSG por el método de Westergren",
    "Sangre total con citrato",
    (
        ("Velocidad de sedimentación", (
            Analyte("vsg_1h", "VSG primera hora", "mm/h", "Varones 0 a 15 · Mujeres 0 a 20"),
            Analyte("vsg_2h", "VSG segunda hora", "mm/h", "Hasta el doble de la primera hora"),
        )),
    ),
)

LAB_PCR = lab_report(
    "LAB-PCR",
    "Proteína C reactiva",
    "PCR cualitativa por látex y cuantitativa",
    "Suero",
    (
        ("Proteína C reactiva", (
            Analyte("pcr_cualitativa", "PCR cualitativa", type="select",
                    options=NEGATIVO_POSITIVO, default="Negativo", reference="Negativo"),
            Analyte("pcr_cuantitativa", "PCR cuantitativa", "mg/L", "Hasta 6"),
        )),
    ),
)

LAB_RPR = lab_report(
    "LAB-RPR",
    "Prueba serológica RPR / VDRL",
    "Descarte de sífilis, cualitativo y por diluciones",
    "Suero",
    (
        ("Inmunología", (
            Analyte("rpr", "RPR / VDRL", type="select", options=NO_REACTIVO,
                    default="No reactivo", reference="No reactivo"),
            Analyte("dilucion", "Título de la dilución", type="text", reference="No aplica si es no reactivo"),
        )),
    ),
)

LAB_VIH = lab_report(
    "LAB-VIH",
    "Prueba rápida de VIH",
    "Tamizaje de VIH 1 y 2, con consejería previa",
    "Sangre total o suero",
    (
        ("Tamizaje", (
            Analyte("vih", "VIH 1 y 2", type="select", options=NO_REACTIVO,
                    default="No reactivo", reference="No reactivo"),
            Analyte("prueba_usada", "Prueba utilizada", type="text"),
        )),
    ),
)

LAB_HEPATITIS = lab_report(
    "LAB-HBS",
    "Marcadores de hepatitis",
    "Antígeno australiano HBsAg, anti VHC y hepatitis A IgM",
    "Suero",
    (
        ("Marcadores virales", (
            Analyte("hbsag", "Antígeno de superficie HBsAg", type="select", options=NO_REACTIVO,
                    default="No reactivo", reference="No reactivo"),
            Analyte("anti_vhc", "Anticuerpos anti VHC", type="select", options=NO_REACTIVO,
                    default="No reactivo", reference="No reactivo"),
            Analyte("hav_igm", "Hepatitis A IgM", type="select", options=NO_REACTIVO,
                    default="No reactivo", reference="No reactivo"),
        )),
    ),
)

LAB_DENGUE = lab_report(
    "LAB-DEN",
    "Prueba rápida de dengue",
    "Antígeno NS1 y anticuerpos IgM e IgG",
    "Suero",
    (
        ("Dengue", (
            Analyte("ns1", "Antígeno NS1", type="select", options=NEGATIVO_POSITIVO,
                    default="Negativo", reference="Negativo"),
            Analyte("dengue_igm", "Anticuerpos IgM", type="select", options=NEGATIVO_POSITIVO,
                    default="Negativo", reference="Negativo"),
            Analyte("dengue_igg", "Anticuerpos IgG", type="select", options=NEGATIVO_POSITIVO,
                    default="Negativo", reference="Negativo"),
        )),
    ),
)

LAB_HELICOBACTER = lab_report(
    "LAB-HPY",
    "Helicobacter pylori",
    "Prueba rápida en sangre o en heces",
    "Suero o heces",
    (
        ("Helicobacter pylori", (
            Analyte("hpylori", "Helicobacter pylori", type="select", options=NEGATIVO_POSITIVO,
                    default="Negativo", reference="Negativo"),
            Analyte("hpylori_muestra", "Tipo de muestra analizada", type="select",
                    options=opts("Sangre", "Heces"), default="Sangre"),
        )),
    ),
)

LAB_AGLUTINACIONES = lab_report(
    "LAB-AGL",
    "Aglutinaciones febriles",
    "Reacción de Widal y Brucella en lámina",
    "Suero",
    (
        ("Aglutinaciones", (
            Analyte("tifico_o", "Antígeno tífico O", type="text", reference="Menor de 1/80"),
            Analyte("tifico_h", "Antígeno tífico H", type="text", reference="Menor de 1/80"),
            Analyte("paratifico_a", "Antígeno paratífico A", type="text", reference="Menor de 1/80"),
            Analyte("paratifico_b", "Antígeno paratífico B", type="text", reference="Menor de 1/80"),
            Analyte("brucella", "Brucella abortus", type="select", options=NEGATIVO_POSITIVO,
                    default="Negativo", reference="Negativo"),
        )),
    ),
)

LAB_EMBARAZO = lab_report(
    "LAB-EMB",
    "Diagnóstico de embarazo",
    "Subunidad beta HCG cualitativa en orina o cuantitativa en sangre",
    "Orina o suero",
    (
        ("Gonadotropina coriónica", (
            Analyte("hcg_cualitativo", "HCG cualitativo", type="select", options=NEGATIVO_POSITIVO,
                    default="Negativo", reference="Negativo en la mujer no gestante"),
            Analyte("hcg_cuantitativo", "HCG cuantitativo", "mUI/mL", "Menor de 5 en la mujer no gestante"),
            Analyte("muestra_hcg", "Tipo de muestra analizada", type="select",
                    options=opts("Orina", "Sangre"), default="Orina"),
        )),
    ),
)

LAB_UROCULTIVO = lab_report(
    "LAB-URO",
    "Urocultivo y antibiograma",
    "Recuento de colonias, germen aislado y sensibilidad",
    "Orina de primer chorro medio",
    (
        ("Cultivo", (
            Analyte("recuento", "Recuento de colonias", "UFC/mL", "Menor de 10 000: sin desarrollo significativo", type="text"),
            Analyte("germen", "Germen aislado", type="text", reference="Ausencia de desarrollo bacteriano"),
        )),
        ("Antibiograma", (
            Analyte("sensibles", "Antibióticos sensibles", type="text"),
            Analyte("intermedios", "Antibióticos de sensibilidad intermedia", type="text"),
            Analyte("resistentes", "Antibióticos resistentes", type="text"),
        )),
    ),
)

LAB_GRAM = lab_report(
    "LAB-GRM",
    "Examen directo y coloración Gram",
    "Secreción vaginal, uretral, faríngea o de herida",
    "Secreción",
    (
        ("Examen directo", (
            Analyte("origen_muestra", "Origen de la muestra", type="text"),
            Analyte("celulas_gram", "Células epiteliales", type="select", options=NO_SE_OBSERVA, default="Escasos"),
            Analyte("leucocitos_gram", "Leucocitos", "por campo", "0 a 5", type="text"),
            Analyte("trichomonas", "Trichomonas vaginalis", type="select", options=NO_SE_OBSERVA,
                    default="No se observa", reference="No se observa"),
            Analyte("clue_cells", "Clue cells", type="select", options=NO_SE_OBSERVA,
                    default="No se observa", reference="No se observa"),
        )),
        ("Coloración Gram", (
            Analyte("gram_positivos", "Cocos y bacilos Gram positivos", type="select",
                    options=NO_SE_OBSERVA, default="No se observa"),
            Analyte("gram_negativos", "Cocos y bacilos Gram negativos", type="select",
                    options=NO_SE_OBSERVA, default="No se observa"),
            Analyte("levaduras_gram", "Levaduras y pseudohifas", type="select",
                    options=NO_SE_OBSERVA, default="No se observa", reference="No se observa"),
        )),
    ),
)

LAB_BACILOSCOPIA = lab_report(
    "LAB-BK",
    "Baciloscopía de esputo (BK)",
    "Búsqueda de bacilos ácido alcohol resistentes por Ziehl-Neelsen",
    "Esputo",
    (
        ("Baciloscopía", (
            Analyte("bk_muestra1", "Primera muestra", type="select",
                    options=opts("Negativo", "Paucibacilar", "Positivo (+)", "Positivo (++)", "Positivo (+++)"),
                    default="Negativo", reference="Negativo"),
            Analyte("bk_muestra2", "Segunda muestra", type="select",
                    options=opts("No procesada", "Negativo", "Paucibacilar", "Positivo (+)", "Positivo (++)", "Positivo (+++)"),
                    default="No procesada"),
            Analyte("bk_muestra3", "Tercera muestra", type="select",
                    options=opts("No procesada", "Negativo", "Paucibacilar", "Positivo (+)", "Positivo (++)", "Positivo (+++)"),
                    default="No procesada"),
        )),
    ),
)

LAB_GOTA_GRUESA = lab_report(
    "LAB-GOT",
    "Gota gruesa para malaria",
    "Búsqueda de Plasmodium y determinación de la especie",
    "Sangre capilar",
    (
        ("Gota gruesa", (
            Analyte("plasmodium", "Plasmodium", type="select", options=NEGATIVO_POSITIVO,
                    default="Negativo", reference="Negativo"),
            Analyte("especie", "Especie identificada", type="select",
                    options=opts("No aplica", "Plasmodium vivax", "Plasmodium falciparum", "Infección mixta"),
                    default="No aplica"),
            Analyte("parasitemia", "Parasitemia", "parásitos/µL", "No aplica si es negativo", type="text"),
        )),
    ),
)

LAB_HONGOS = lab_report(
    "LAB-KOH",
    "Examen directo con KOH para hongos",
    "Raspado de piel, uñas o cuero cabelludo",
    "Raspado de piel o uñas",
    (
        ("Examen micológico directo", (
            Analyte("zona_raspado", "Zona del raspado", type="text"),
            Analyte("hifas", "Hifas", type="select", options=NO_SE_OBSERVA,
                    default="No se observa", reference="No se observa"),
            Analyte("esporas", "Esporas", type="select", options=NO_SE_OBSERVA,
                    default="No se observa", reference="No se observa"),
            Analyte("levaduras_koh", "Levaduras", type="select", options=NO_SE_OBSERVA,
                    default="No se observa", reference="No se observa"),
        )),
    ),
)

LAB_LEISHMANIASIS = lab_report(
    "LAB-LEI",
    "Frotis para leishmaniasis",
    "Búsqueda de amastigotes en el borde de la lesión",
    "Frotis del borde de la lesión",
    (
        ("Frotis", (
            Analyte("lesion", "Ubicación de la lesión", type="text"),
            Analyte("amastigotes", "Amastigotes de Leishmania", type="select", options=NEGATIVO_POSITIVO,
                    default="Negativo", reference="Negativo"),
            Analyte("carga", "Carga parasitaria", type="select",
                    options=opts("No aplica", "Escasa", "Moderada", "Abundante"), default="No aplica"),
        )),
    ),
)

LAB_PROTEINURIA = lab_report(
    "LAB-PRO",
    "Proteinuria de 24 horas",
    "Volumen, concentración y excreción total de proteínas",
    "Orina de 24 horas",
    (
        ("Proteinuria", (
            Analyte("volumen_proteinuria", "Volumen urinario recolectado", "mL", "800 a 2 000"),
            Analyte("proteinas_concentracion", "Proteínas", "mg/dL", "Hasta 10"),
            Analyte("proteinuria_total", "Proteinuria total", "mg/24 h", "Hasta 150"),
            Analyte("creatinuria", "Creatinina en orina", "mg/24 h", "Varones 800 a 2 000 · Mujeres 600 a 1 800"),
        )),
    ),
)

INFORME_RADIOLOGICO = {
    "code": "RX-INF",
    "version": 1,
    "family": INFORME,
    "title": "Informe radiológico",
    "description": "Lectura e informe de un estudio de Rayos X",
    "study_type": "RAYOS_X",
    "requires_signature": True,
    "fields": [
        {"key": "estudio", "label": "Estudio realizado", "type": "text", "group": "Estudio", "required": True, "wide": True},
        {"key": "proyecciones", "label": "Proyecciones", "type": "text", "group": "Estudio", "placeholder": "Frontal y lateral"},
        FIELD_MOTIVO,
        {"key": "comparacion", "label": "Estudios previos comparados", "type": "text", "group": "Estudio", "default": "No se dispone de estudios previos", "wide": True},
        {"key": "hallazgos", "label": "Hallazgos", "type": "textarea", "group": "Lectura", "required": True, "wide": True},
        {"key": "limitaciones", "label": "Limitaciones del estudio", "type": "text", "group": "Lectura", "default": "Ninguna", "wide": True},
        FIELD_CONCLUSION,
    ],
    "body": (
        HEADER_CLINICAL
        + """<table class="doc-grid">
<tr><td class="k">Estudio</td><td>{{ campo.estudio }}</td>
    <td class="k">Proyecciones</td><td>{{ campo.proyecciones }}</td></tr>
<tr><td class="k">Motivo</td><td>{{ campo.motivo }}</td>
    <td class="k">Comparación</td><td>{{ campo.comparacion }}</td></tr>
</table>

<h2>Hallazgos</h2>
<p>{{ campo.hallazgos|parrafos }}</p>
<p><strong>Limitaciones del estudio:</strong> {{ campo.limitaciones }}</p>

<h2>Conclusión</h2>
<p>{{ campo.conclusion|parrafos }}</p>"""
        + SIGN_DOCTOR
        + '<p class="doc-note">El informe radiológico es un medio de ayuda diagnóstica '
        "y debe ser correlacionado con la evaluación clínica del paciente.</p>"
    ),
}

INFORME_AUDIOMETRIA = {
    "code": "AUD",
    "version": 1,
    "family": INFORME,
    "title": "Informe de audiometría",
    "description": "Umbrales por vía aérea y ósea, y conclusión audiológica",
    "study_type": "OTRO",
    "requires_signature": True,
    "fields": [
        FIELD_MOTIVO,
        {"key": "otoscopia_od", "label": "Otoscopía · oído derecho", "type": "text", "group": "Otoscopía", "default": "Conducto permeable, tímpano íntegro"},
        {"key": "otoscopia_oi", "label": "Otoscopía · oído izquierdo", "type": "text", "group": "Otoscopía", "default": "Conducto permeable, tímpano íntegro"},
        *[
            measure(f"{via}_{oido}_{hz}", f"{titulo} · {lado} · {hz} Hz", f"Vía {titulo.lower()}")
            for via, titulo in (("aerea", "Aérea"), ("osea", "Ósea"))
            for oido, lado in (("od", "OD"), ("oi", "OI"))
            for hz in ("500", "1000", "2000", "4000")
        ],
        {"key": "promedio_od", "label": "Promedio tonal · OD (dB)", "type": "number", "group": "Conclusión"},
        {"key": "promedio_oi", "label": "Promedio tonal · OI (dB)", "type": "number", "group": "Conclusión"},
        choice("grado_od", "Grado de pérdida · OD", "Conclusión",
               opts("Audición normal", "Hipoacusia leve", "Hipoacusia moderada", "Hipoacusia severa", "Hipoacusia profunda"),
               "Audición normal"),
        choice("grado_oi", "Grado de pérdida · OI", "Conclusión",
               opts("Audición normal", "Hipoacusia leve", "Hipoacusia moderada", "Hipoacusia severa", "Hipoacusia profunda"),
               "Audición normal"),
        FIELD_CONCLUSION,
    ],
    "body": (
        HEADER_CLINICAL
        + """<p><strong>Motivo del examen:</strong> {{ campo.motivo }}</p>

<h2>Otoscopía</h2>
<table class="doc-grid">
<tr><td class="k">Oído derecho</td><td>{{ campo.otoscopia_od }}</td></tr>
<tr><td class="k">Oído izquierdo</td><td>{{ campo.otoscopia_oi }}</td></tr>
</table>

<h2>Umbrales auditivos (dB)</h2>
<table class="doc-table">
<tr><th>Vía</th><th>Oído</th><th>500 Hz</th><th>1 000 Hz</th><th>2 000 Hz</th><th>4 000 Hz</th></tr>
<tr><td>Aérea</td><td>Derecho</td><td>{{ campo.aerea_od_500 }}</td><td>{{ campo.aerea_od_1000 }}</td>
    <td>{{ campo.aerea_od_2000 }}</td><td>{{ campo.aerea_od_4000 }}</td></tr>
<tr><td>Aérea</td><td>Izquierdo</td><td>{{ campo.aerea_oi_500 }}</td><td>{{ campo.aerea_oi_1000 }}</td>
    <td>{{ campo.aerea_oi_2000 }}</td><td>{{ campo.aerea_oi_4000 }}</td></tr>
<tr><td>Ósea</td><td>Derecho</td><td>{{ campo.osea_od_500 }}</td><td>{{ campo.osea_od_1000 }}</td>
    <td>{{ campo.osea_od_2000 }}</td><td>{{ campo.osea_od_4000 }}</td></tr>
<tr><td>Ósea</td><td>Izquierdo</td><td>{{ campo.osea_oi_500 }}</td><td>{{ campo.osea_oi_1000 }}</td>
    <td>{{ campo.osea_oi_2000 }}</td><td>{{ campo.osea_oi_4000 }}</td></tr>
</table>

<table class="doc-grid">
<tr><td class="k">Promedio tonal OD</td><td>{{ campo.promedio_od }} dB</td>
    <td class="k">Grado</td><td>{{ campo.grado_od }}</td></tr>
<tr><td class="k">Promedio tonal OI</td><td>{{ campo.promedio_oi }} dB</td>
    <td class="k">Grado</td><td>{{ campo.grado_oi }}</td></tr>
</table>

<h2>Conclusión</h2>
<p>{{ campo.conclusion|parrafos }}</p>"""
        + SIGN_DOCTOR
    ),
}

INFORME_ESPIROMETRIA = {
    "code": "ESP",
    "version": 1,
    "family": INFORME,
    "title": "Informe de espirometría",
    "description": "CVF, VEF1, relación VEF1/CVF e interpretación",
    "study_type": "OTRO",
    "requires_signature": True,
    "fields": [
        FIELD_MOTIVO,
        measure("talla_esp", "Talla (cm)", "Datos del examen"),
        measure("peso_esp", "Peso (kg)", "Datos del examen"),
        choice("tabaquismo", "Antecedente de tabaquismo", "Datos del examen", SI_NO, "No"),
        measure("cvf", "CVF (litros)", "Valores obtenidos"),
        measure("cvf_porcentaje", "CVF (% del predicho)", "Valores obtenidos"),
        measure("vef1", "VEF1 (litros)", "Valores obtenidos"),
        measure("vef1_porcentaje", "VEF1 (% del predicho)", "Valores obtenidos"),
        measure("relacion", "Relación VEF1/CVF (%)", "Valores obtenidos"),
        measure("fef", "FEF 25-75 % (litros/segundo)", "Valores obtenidos"),
        choice("patron", "Patrón ventilatorio", "Interpretación",
               opts("Normal", "Obstructivo", "Restrictivo", "Mixto"), "Normal"),
        choice("severidad_esp", "Severidad", "Interpretación",
               opts("No aplica", "Leve", "Moderada", "Severa"), "No aplica"),
        choice("colaboracion", "Colaboración del paciente", "Interpretación",
               opts("Adecuada", "Regular", "Deficiente"), "Adecuada"),
        FIELD_CONCLUSION,
    ],
    "body": (
        HEADER_CLINICAL
        + """<p><strong>Motivo del examen:</strong> {{ campo.motivo }}</p>
<table class="doc-grid">
<tr><td class="k">Talla</td><td>{{ campo.talla_esp }} cm</td>
    <td class="k">Peso</td><td>{{ campo.peso_esp }} kg</td></tr>
<tr><td class="k">Tabaquismo</td><td>{{ campo.tabaquismo }}</td>
    <td class="k">Colaboración</td><td>{{ campo.colaboracion }}</td></tr>
</table>

<h2>Valores obtenidos</h2>
<table class="doc-table">
<tr><th>Parámetro</th><th>Valor</th><th>% del predicho</th></tr>
<tr><td>CVF</td><td>{{ campo.cvf }} L</td><td>{{ campo.cvf_porcentaje }} %</td></tr>
<tr><td>VEF1</td><td>{{ campo.vef1 }} L</td><td>{{ campo.vef1_porcentaje }} %</td></tr>
<tr><td>VEF1 / CVF</td><td>{{ campo.relacion }} %</td><td>Referencia: mayor de 70 %</td></tr>
<tr><td>FEF 25-75 %</td><td>{{ campo.fef }} L/s</td><td></td></tr>
</table>

<h2>Interpretación</h2>
<table class="doc-grid">
<tr><td class="k">Patrón ventilatorio</td><td>{{ campo.patron }}</td>
    <td class="k">Severidad</td><td>{{ campo.severidad_esp }}</td></tr>
</table>
<p>{{ campo.conclusion|parrafos }}</p>"""
        + SIGN_DOCTOR
    ),
}


# --- Familia B · Fichas clínicas ------------------------------------------

FICHA_OPTOMETRIA = {
    "code": "FIC-OPT",
    "version": 1,
    "family": FICHA,
    "title": "Ficha de optometría",
    "description": "Agudeza visual, test de colores y estereopsis",
    "study_type": "OPTOMETRIA",
    "requires_signature": True,
    "fields": [
        {"key": "empresa", "label": "Empresa", "type": "text", "group": "Postulante"},
        {"key": "puesto", "label": "Puesto", "type": "text", "group": "Postulante"},
        {"key": "lejos_od", "label": "Visión de lejos · OD", "type": "text", "group": "Agudeza visual", "placeholder": "20/20"},
        {"key": "lejos_oi", "label": "Visión de lejos · OI", "type": "text", "group": "Agudeza visual", "placeholder": "20/20"},
        {"key": "cerca_od", "label": "Visión de cerca · OD", "type": "text", "group": "Agudeza visual", "placeholder": "J1"},
        {"key": "cerca_oi", "label": "Visión de cerca · OI", "type": "text", "group": "Agudeza visual", "placeholder": "J1"},
        choice("test_mosca", "Test de la mosca (estereopsis)", "Pruebas", opts("Normal", "Alterado"), "Normal"),
        choice("test_colores", "Test de colores", "Pruebas", opts("Normal", "Discromatopsia"), "Normal"),
        choice("movilidad", "Movilidad ocular", "Pruebas", opts("Conservada", "Alterada"), "Conservada"),
        choice("reflejos", "Reflejos pupilares", "Pruebas", opts("Conservados", "Alterados"), "Conservados"),
        {"key": "conclusion", "label": "Conclusión y restricciones", "type": "textarea", "group": "Conclusión", "required": True, "wide": True},
    ],
    "body": (
        HEADER_CLINICAL
        + """<table class="doc-grid">
<tr><td class="k">Empresa</td><td>{{ campo.empresa }}</td>
    <td class="k">Puesto</td><td>{{ campo.puesto }}</td></tr>
</table>

<h2>Agudeza visual</h2>
<table class="doc-table">
<tr><th></th><th>Ojo derecho</th><th>Ojo izquierdo</th></tr>
<tr><td>Visión de lejos</td><td>{{ campo.lejos_od }}</td><td>{{ campo.lejos_oi }}</td></tr>
<tr><td>Visión de cerca</td><td>{{ campo.cerca_od }}</td><td>{{ campo.cerca_oi }}</td></tr>
</table>

<h2>Pruebas complementarias</h2>
<table class="doc-grid">
<tr><td class="k">Test de la mosca</td><td>{{ campo.test_mosca }}</td>
    <td class="k">Test de colores</td><td>{{ campo.test_colores }}</td></tr>
<tr><td class="k">Movilidad ocular</td><td>{{ campo.movilidad }}</td>
    <td class="k">Reflejos pupilares</td><td>{{ campo.reflejos }}</td></tr>
</table>

<h2>Conclusión</h2>
<p>{{ campo.conclusion|parrafos }}</p>"""
        + SIGN_DOCTOR
    ),
}

RECETA_LENTES = {
    "code": "REC-LEN",
    "version": 1,
    "family": FICHA,
    "title": "Receta para prescripción de lentes",
    "description": "Medidas de lejos y cerca por ojo",
    "study_type": "OPTOMETRIA",
    "requires_signature": True,
    "fields": [
        {"key": "proximo_control", "label": "Próximo control", "type": "date", "group": "Receta"},
        *[
            {"key": f"{dist}_{eye}_{part}", "label": f"{title} · {eye.upper()} · {part_label}", "type": "text", "group": title}
            for dist, title in (("lejos", "Visión de lejos"), ("cerca", "Visión de cerca"))
            for eye in ("od", "oi")
            for part, part_label in (("esfera", "Esfera"), ("cilindro", "Cilindro"), ("eje", "Eje"), ("dip", "DIP"), ("av", "AV"))
        ],
        {"key": "observaciones", "label": "Observaciones", "type": "textarea", "group": "Receta", "wide": True},
    ],
    "body": (
        HEADER_CLINICAL
        + """<table class="doc-grid">
<tr><td class="k">Próximo control</td><td>{{ campo.proximo_control }}</td></tr>
</table>

<h2>Visión de lejos</h2>
<table class="doc-table">
<tr><th></th><th>Esfera</th><th>Cilindro</th><th>Eje</th><th>DIP</th><th>AV</th></tr>
<tr><td>OD</td><td>{{ campo.lejos_od_esfera }}</td><td>{{ campo.lejos_od_cilindro }}</td>
    <td>{{ campo.lejos_od_eje }}</td><td>{{ campo.lejos_od_dip }}</td><td>{{ campo.lejos_od_av }}</td></tr>
<tr><td>OI</td><td>{{ campo.lejos_oi_esfera }}</td><td>{{ campo.lejos_oi_cilindro }}</td>
    <td>{{ campo.lejos_oi_eje }}</td><td>{{ campo.lejos_oi_dip }}</td><td>{{ campo.lejos_oi_av }}</td></tr>
</table>

<h2>Visión de cerca</h2>
<table class="doc-table">
<tr><th></th><th>Esfera</th><th>Cilindro</th><th>Eje</th><th>DIP</th><th>AV</th></tr>
<tr><td>OD</td><td>{{ campo.cerca_od_esfera }}</td><td>{{ campo.cerca_od_cilindro }}</td>
    <td>{{ campo.cerca_od_eje }}</td><td>{{ campo.cerca_od_dip }}</td><td>{{ campo.cerca_od_av }}</td></tr>
<tr><td>OI</td><td>{{ campo.cerca_oi_esfera }}</td><td>{{ campo.cerca_oi_cilindro }}</td>
    <td>{{ campo.cerca_oi_eje }}</td><td>{{ campo.cerca_oi_dip }}</td><td>{{ campo.cerca_oi_av }}</td></tr>
</table>

<h2>Recomendaciones al paciente</h2>
<ol>
<li>Acuda personalmente al óptico para el correcto centrado de sus lentes.</li>
<li>Vuelva a este establecimiento para el control de su visión.</li>
<li>Es esperable que al inicio sienta ligera incomodidad en la visión a distancia,
    como elevación del piso o sensación de mareo.</li>
</ol>
<p><strong>Observaciones:</strong> {{ campo.observaciones|parrafos }}</p>"""
        + SIGN_DOCTOR
    ),
}

_EPWORTH_SITUATIONS: tuple[tuple[str, str], ...] = (
    ("s1", "Sentado leyendo"),
    ("s2", "Viendo televisión"),
    ("s3", "Sentado sin actividad en un lugar público"),
    ("s4", "Como pasajero en un vehículo durante una hora o menos de recorrido"),
    ("s5", "Recostado en la tarde, si las circunstancias lo permiten"),
    ("s6", "Sentado conversando con alguien"),
    ("s7", "Sentado luego del almuerzo, sin haber bebido alcohol"),
    ("s8", "Conduciendo, cuando se detiene algunos minutos por razones de tráfico"),
    ("s9", "Parado, apoyándose o no en una pared o mueble"),
)

_EPWORTH_OPTIONS = [
    {"value": "0", "label": "0 — Nunca cabecearía"},
    {"value": "1", "label": "1 — Poca probabilidad"},
    {"value": "2", "label": "2 — Moderada probabilidad"},
    {"value": "3", "label": "3 — Alta probabilidad"},
]

RECETA_MEDICA = {
    "code": "REC-MED",
    "version": 1,
    "family": FICHA,
    "title": "Receta médica",
    "description": "Medicamentos e indicaciones de la atención, para entregar al paciente",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "indicaciones_adicionales", "label": "Indicaciones adicionales", "type": "textarea", "group": "Receta", "wide": True,
         "help": "Se suman a las indicaciones ya registradas en la atención."},
        {"key": "proximo_control", "label": "Próximo control", "type": "date", "group": "Receta"},
        {"key": "validez_dias", "label": "Validez de la receta (días)", "type": "number", "group": "Receta", "default": 30},
    ],
    "body": (
        """<table class="doc-grid">
<tr><td class="k">Paciente</td><td>{{ paciente.nombre_completo }}</td>
    <td class="k">Historia</td><td>{{ paciente.historia }}</td></tr>
<tr><td class="k">Documento</td><td>{{ paciente.tipo_documento }} {{ paciente.documento }}</td>
    <td class="k">Edad</td><td>{{ paciente.edad }}</td></tr>
<tr><td class="k">Fecha</td><td>{{ fecha.hoy }}</td>
    <td class="k">Alergias</td><td>{{ paciente.alergias }}</td></tr>
<tr><td class="k">Diagnóstico</td><td colspan="3">{{ atencion.diagnosticos|lista }}</td></tr>
</table>

<h2>Prescripción</h2>
{{ atencion.medicamentos|lista }}

<h2>Indicaciones</h2>
<p>{{ atencion.indicaciones|parrafos }}</p>
<p>{{ campo.indicaciones_adicionales|parrafos }}</p>

<table class="doc-grid">
<tr><td class="k">Próximo control</td><td>{{ campo.proximo_control }}</td>
    <td class="k">Validez</td><td>{{ campo.validez_dias }} días</td></tr>
</table>

<p class="doc-note">Los medicamentos y las indicaciones se toman de la atención
vinculada a esta receta. No se automedique ni modifique las dosis indicadas.</p>"""
        + SIGN_DOCTOR
    ),
}

FICHA_EPWORTH = {
    "code": "FIC-EPW",
    "version": 1,
    "family": FICHA,
    "title": "Ficha de evaluación de fatiga y somnolencia",
    "description": "Escala de somnolencia de Epworth para conductores",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        choice("conduce", "¿Conduce vehículos motorizados?", "Antecedente", opts("Sí", "No"), "Sí"),
        *[
            {
                "key": key,
                "label": label,
                "type": "select",
                "group": "Probabilidad de cabecear",
                "options": _EPWORTH_OPTIONS,
                "default": "0",
                "wide": True,
            }
            for key, label in _EPWORTH_SITUATIONS
        ],
        {
            "key": "puntaje",
            "label": "Puntaje total",
            "type": "computed",
            "group": "Resultado",
            "sum": [key for key, _ in _EPWORTH_SITUATIONS],
            "help": "Un puntaje mayor a 10 se considera positivo para somnolencia diurna excesiva.",
        },
        {"key": "interpretacion", "label": "Interpretación", "type": "textarea", "group": "Resultado", "required": True, "wide": True},
    ],
    "body": (
        HEADER_CLINICAL
        + """<p>¿Qué tan probable es que usted cabecee o se quede dormido en las siguientes
situaciones? Considere los últimos meses de sus actividades habituales. No se refiere
a sentirse cansado por actividad física.</p>

<table class="doc-table">
<tr><th>Situación</th><th>Puntaje</th></tr>
<tr><td>Sentado leyendo</td><td>{{ campo.s1 }}</td></tr>
<tr><td>Viendo televisión</td><td>{{ campo.s2 }}</td></tr>
<tr><td>Sentado sin actividad en un lugar público</td><td>{{ campo.s3 }}</td></tr>
<tr><td>Como pasajero en un vehículo durante una hora o menos</td><td>{{ campo.s4 }}</td></tr>
<tr><td>Recostado en la tarde, si las circunstancias lo permiten</td><td>{{ campo.s5 }}</td></tr>
<tr><td>Sentado conversando con alguien</td><td>{{ campo.s6 }}</td></tr>
<tr><td>Sentado luego del almuerzo, sin haber bebido alcohol</td><td>{{ campo.s7 }}</td></tr>
<tr><td>Conduciendo, cuando se detiene por razones de tráfico</td><td>{{ campo.s8 }}</td></tr>
<tr><td>Parado, apoyándose o no en una pared o mueble</td><td>{{ campo.s9 }}</td></tr>
</table>

<table class="doc-grid">
<tr><td class="k">Conduce vehículos motorizados</td><td>{{ campo.conduce }}</td>
    <td class="k">Puntaje total</td><td><strong>{{ campo.puntaje }}</strong></td></tr>
</table>
<p class="doc-note">Cada situación puntúa de 0 a 3. Un puntaje total mayor a 10 se
considera positivo para somnolencia diurna excesiva.</p>

<h2>Interpretación</h2>
<p>{{ campo.interpretacion|parrafos }}</p>"""
        + SIGN_DOCTOR
    ),
}

RIESGO_QUIRURGICO = {
    "code": "FIC-RQX",
    "version": 1,
    "family": FICHA,
    "title": "Evaluación de riesgo quirúrgico",
    "description": "Antecedentes, examen y clasificación del riesgo",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "antecedentes_medicos", "label": "Antecedentes médicos", "type": "textarea", "group": "Antecedentes", "wide": True},
        {"key": "antecedentes_quirurgicos", "label": "Antecedentes quirúrgicos", "type": "textarea", "group": "Antecedentes", "wide": True},
        {"key": "alergias", "label": "Alergias", "type": "text", "group": "Antecedentes", "default": "Niega", "wide": True},
        {"key": "ecg", "label": "Electrocardiograma", "type": "text", "group": "Exámenes", "wide": True},
        {"key": "examen", "label": "Examen físico", "type": "textarea", "group": "Exámenes", "wide": True},
        choice("asa", "Clasificación ASA", "Conclusión", opts("I", "II", "III", "IV"), "I"),
        {"key": "conclusion", "label": "Conclusión del riesgo quirúrgico", "type": "textarea", "group": "Conclusión", "required": True, "wide": True},
    ],
    "body": (
        HEADER_CLINICAL
        + """<h2>Antecedentes</h2>
<table class="doc-grid">
<tr><td class="k">Médicos</td><td>{{ campo.antecedentes_medicos|parrafos }}</td></tr>
<tr><td class="k">Quirúrgicos</td><td>{{ campo.antecedentes_quirurgicos|parrafos }}</td></tr>
<tr><td class="k">Alergias</td><td>{{ campo.alergias }}</td></tr>
</table>

<h2>Evaluación</h2>
<table class="doc-grid">
<tr><td class="k">Presión arterial</td><td>{{ atencion.presion_arterial }}</td>
    <td class="k">Frecuencia cardíaca</td><td>{{ atencion.frecuencia_cardiaca }}</td></tr>
<tr><td class="k">Electrocardiograma</td><td colspan="3">{{ campo.ecg }}</td></tr>
</table>
<p>{{ campo.examen|parrafos }}</p>

<h2>Conclusión</h2>
<p><strong>Clasificación ASA:</strong> {{ campo.asa }}</p>
<p>{{ campo.conclusion|parrafos }}</p>"""
        + SIGN_PATIENT_DOCTOR
    ),
}


EVALUACION_PSICOSOMATICA = {
    "code": "FIC-PSM",
    "version": 1,
    "family": FICHA,
    "title": "Informe médico de evaluación psicosomática",
    "description": "Evaluación multidisciplinaria para licencia de conducir",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "categoria_licencia", "label": "Categoría de licencia", "type": "text", "group": "Postulante", "placeholder": "A-IIb"},
        choice("condicion", "Condición", "Postulante", opts("Primera vez", "Revalidación", "Recategorización"), "Revalidación"),
        {"key": "estudios", "label": "Estudios alcanzados", "type": "text", "group": "Postulante", "wide": True},
        {"key": "grupo_sanguineo", "label": "Grupo sanguíneo", "type": "text", "group": "Laboratorio", "placeholder": "O"},
        choice("factor_rh", "Factor Rh", "Laboratorio", opts("Positivo", "Negativo"), "Positivo"),
        *[
            choice(key, label, "Laboratorio", NEGATIVO_POSITIVO, "Negativo")
            for key, label in (
                ("cocaina", "Cocaína"),
                ("marihuana", "Marihuana"),
                ("alcoholimetria", "Alcoholimetría"),
            )
        ],
        measure("frecuencia_cardiaca", "Frecuencia cardíaca (lpm)", "Medicina general"),
        measure("frecuencia_respiratoria", "Frecuencia respiratoria (rpm)", "Medicina general"),
        {"key": "presion_arterial", "label": "Presión arterial", "type": "text", "group": "Medicina general", "placeholder": "120/80 mmHg"},
        {"key": "auscultacion", "label": "Auscultación de tórax", "type": "text", "group": "Medicina general", "default": "Sin alteraciones", "wide": True},
        *[
            choice(key, label, "Capacidad funcional", NORMAL_ALTERADO_SIMPLE, "Normal")
            for key, label in (
                ("fuerza_muscular", "Fuerza muscular"),
                ("indice_indice", "Prueba índice – índice"),
                ("romberg", "Prueba de Romberg"),
                ("indice_nariz", "Prueba índice – nariz"),
            )
        ],
        *[
            choice(key, label, "Movimientos involuntarios", AUSENTE_PRESENTE, "Ausente")
            for key, label in (("corea_atetosis", "Corea – atetosis"), ("parkinson", "Parkinson"))
        ],
        choice("columna", "Columna vertebral", "Lesiones deformantes", SIN_LESIONES, "Sin lesiones"),
        choice("extremidades", "Extremidades", "Lesiones deformantes", SIN_LESIONES, "Sin lesiones"),
        {"key": "av_sc_od", "label": "Agudeza visual sin corrección · OD", "type": "text", "group": "Oftalmología", "placeholder": "20/20"},
        {"key": "av_sc_oi", "label": "Agudeza visual sin corrección · OI", "type": "text", "group": "Oftalmología", "placeholder": "20/20"},
        {"key": "av_cc_od", "label": "Agudeza visual con corrección · OD", "type": "text", "group": "Oftalmología", "placeholder": "20/20"},
        {"key": "av_cc_oi", "label": "Agudeza visual con corrección · OI", "type": "text", "group": "Oftalmología", "placeholder": "20/20"},
        {"key": "restricciones_oftalmologicas", "label": "Restricciones oftalmológicas", "type": "text", "group": "Oftalmología", "default": "Ninguna", "wide": True},
        {"key": "oido_externo", "label": "Examen externo", "type": "text", "group": "Otorrinolaringología", "default": "Sin alteraciones"},
        {"key": "otoscopia", "label": "Otoscopía", "type": "text", "group": "Otorrinolaringología", "default": "Sin alteraciones"},
        {"key": "audiometria_od", "label": "Audiometría · OD", "type": "text", "group": "Otorrinolaringología"},
        {"key": "audiometria_oi", "label": "Audiometría · OI", "type": "text", "group": "Otorrinolaringología"},
        {"key": "restricciones_orl", "label": "Restricciones otorrinolaringológicas", "type": "text", "group": "Otorrinolaringología", "default": "Ninguna", "wide": True},
        {"key": "test_reaccion", "label": "Test de reacción", "type": "text", "group": "Psicología", "default": "Dentro de lo normal"},
        {"key": "test_palanca", "label": "Test de palanca", "type": "text", "group": "Psicología", "default": "Dentro de lo normal"},
        {"key": "test_punteado", "label": "Test de punteado", "type": "text", "group": "Psicología", "default": "Dentro de lo normal"},
        *[
            choice(key, label, "Psicología", NORMAL_ALTERADO_SIMPLE, "Normal")
            for key, label in (
                ("organicidad", "Organicidad"),
                ("psicomotricidad", "Psicomotricidad"),
                ("psicopatologia", "Psicopatología"),
                ("inteligencia", "Inteligencia"),
            )
        ],
        {"key": "restricciones_psicologicas", "label": "Restricciones psicológicas", "type": "text", "group": "Psicología", "default": "Ninguna", "wide": True},
        choice("aptitud", "Resultado de la evaluación", "Conclusión", opts("APTO", "APTO CON RESTRICCIONES", "NO APTO"), "APTO"),
        {"key": "conclusion", "label": "Conclusión y restricciones", "type": "textarea", "group": "Conclusión", "required": True, "wide": True},
    ],
    "body": (
        """<table class="doc-grid">
<tr><td class="k">Informe N.°</td><td>{{ documento.numero }}</td>
    <td class="k">Fecha</td><td>{{ fecha.hoy }}</td></tr>
<tr><td class="k">Postulante</td><td colspan="3">{{ paciente.nombre_completo }}</td></tr>
<tr><td class="k">Documento</td><td>{{ paciente.tipo_documento }} {{ paciente.documento }}</td>
    <td class="k">Fecha de nacimiento</td><td>{{ paciente.fecha_nacimiento }}</td></tr>
<tr><td class="k">Edad</td><td>{{ paciente.edad }}</td>
    <td class="k">Sexo</td><td>{{ paciente.sexo }}</td></tr>
<tr><td class="k">Domicilio</td><td colspan="3">{{ paciente.direccion }}</td></tr>
<tr><td class="k">Estudios alcanzados</td><td>{{ campo.estudios }}</td>
    <td class="k">Categoría / condición</td><td>{{ campo.categoria_licencia }} · {{ campo.condicion }}</td></tr>
</table>

<h2>Grupo sanguíneo y toxicológico</h2>
<table class="doc-grid">
<tr><td class="k">Grupo sanguíneo</td><td>{{ campo.grupo_sanguineo }}</td>
    <td class="k">Factor Rh</td><td>{{ campo.factor_rh }}</td></tr>
<tr><td class="k">Cocaína</td><td>{{ campo.cocaina }}</td>
    <td class="k">Marihuana</td><td>{{ campo.marihuana }}</td></tr>
<tr><td class="k">Alcoholimetría</td><td colspan="3">{{ campo.alcoholimetria }}</td></tr>
</table>

<h2>Medicina general</h2>
<table class="doc-grid">
<tr><td class="k">Frecuencia cardíaca</td><td>{{ campo.frecuencia_cardiaca }} lpm</td>
    <td class="k">Frecuencia respiratoria</td><td>{{ campo.frecuencia_respiratoria }} rpm</td></tr>
<tr><td class="k">Presión arterial</td><td>{{ campo.presion_arterial }}</td>
    <td class="k">Auscultación de tórax</td><td>{{ campo.auscultacion }}</td></tr>
</table>

<h2>Capacidad funcional y fuerza muscular</h2>
<table class="doc-grid">
<tr><td class="k">Fuerza muscular</td><td>{{ campo.fuerza_muscular }}</td>
    <td class="k">Prueba índice – índice</td><td>{{ campo.indice_indice }}</td></tr>
<tr><td class="k">Romberg</td><td>{{ campo.romberg }}</td>
    <td class="k">Prueba índice – nariz</td><td>{{ campo.indice_nariz }}</td></tr>
<tr><td class="k">Corea – atetosis</td><td>{{ campo.corea_atetosis }}</td>
    <td class="k">Parkinson</td><td>{{ campo.parkinson }}</td></tr>
<tr><td class="k">Columna vertebral</td><td>{{ campo.columna }}</td>
    <td class="k">Extremidades</td><td>{{ campo.extremidades }}</td></tr>
</table>

<h2>Examen oftalmológico</h2>
<table class="doc-table">
<tr><th>Agudeza visual</th><th>Ojo derecho</th><th>Ojo izquierdo</th></tr>
<tr><td>Sin corrección</td><td>{{ campo.av_sc_od }}</td><td>{{ campo.av_sc_oi }}</td></tr>
<tr><td>Con corrección</td><td>{{ campo.av_cc_od }}</td><td>{{ campo.av_cc_oi }}</td></tr>
</table>
<p><strong>Restricciones:</strong> {{ campo.restricciones_oftalmologicas }}</p>

<h2>Examen otorrinolaringológico</h2>
<table class="doc-grid">
<tr><td class="k">Examen externo</td><td>{{ campo.oido_externo }}</td>
    <td class="k">Otoscopía</td><td>{{ campo.otoscopia }}</td></tr>
<tr><td class="k">Audiometría OD</td><td>{{ campo.audiometria_od }}</td>
    <td class="k">Audiometría OI</td><td>{{ campo.audiometria_oi }}</td></tr>
</table>
<p><strong>Restricciones:</strong> {{ campo.restricciones_orl }}</p>

<h2>Examen psicológico</h2>
<table class="doc-grid">
<tr><td class="k">Test de reacción</td><td>{{ campo.test_reaccion }}</td>
    <td class="k">Test de palanca</td><td>{{ campo.test_palanca }}</td></tr>
<tr><td class="k">Test de punteado</td><td>{{ campo.test_punteado }}</td>
    <td class="k">Organicidad</td><td>{{ campo.organicidad }}</td></tr>
<tr><td class="k">Psicomotricidad</td><td>{{ campo.psicomotricidad }}</td>
    <td class="k">Psicopatología</td><td>{{ campo.psicopatologia }}</td></tr>
<tr><td class="k">Inteligencia</td><td colspan="3">{{ campo.inteligencia }}</td></tr>
</table>
<p><strong>Restricciones:</strong> {{ campo.restricciones_psicologicas }}</p>

<h2>Conclusión</h2>
<p>Resultado de la evaluación: <strong>{{ campo.aptitud }}</strong></p>
<p>{{ campo.conclusion|parrafos }}</p>"""
        + """<div class="doc-signatures">
<div class="sign"><div class="line"></div><div class="role">Medicina general</div></div>
<div class="sign"><div class="line"></div><div class="role">Oftalmología</div></div>
<div class="sign"><div class="line"></div><div class="role">Otorrinolaringología</div></div>
<div class="sign"><div class="line"></div><div class="role">Psicología</div></div>
</div>"""
    ),
}

INFORME_PSICOLOGICO = {
    "code": "FIC-PSO",
    "version": 1,
    "family": FICHA,
    "title": "Informe psicológico ocupacional",
    "description": "Observación de conductas, resultados y aptitud del postulante",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "empresa", "label": "Empresa", "type": "text", "group": "Postulante"},
        {"key": "puesto", "label": "Puesto que ocupa o postula", "type": "text", "group": "Postulante"},
        choice("tipo_evaluacion", "Tipo de evaluación", "Postulante", opts("Pre ocupacional", "Periódica", "De retiro"), "Pre ocupacional"),
        {"key": "instruccion", "label": "Grado de instrucción", "type": "text", "group": "Postulante"},
        {"key": "residencia", "label": "Lugar de residencia", "type": "text", "group": "Postulante"},
        {"key": "motivo", "label": "Motivo de la evaluación", "type": "text", "group": "Postulante", "wide": True,
         "default": "Requerimiento de la empresa en la que labora"},
        choice("presentacion", "Presentación", "Observación de conductas", opts("Adecuada", "Inadecuada"), "Adecuada"),
        choice("postura", "Postura", "Observación de conductas", opts("Erguida", "Encorvada"), "Erguida"),
        choice("ritmo", "Discurso · ritmo", "Observación de conductas", opts("Fluido", "Lento", "Rápido"), "Fluido"),
        choice("tono", "Discurso · tono", "Observación de conductas", opts("Moderado", "Bajo", "Alto"), "Moderado"),
        choice("articulacion", "Discurso · articulación", "Observación de conductas", opts("Sin dificultad", "Con dificultad"), "Sin dificultad"),
        choice("orientacion_tiempo", "Orientación · tiempo", "Observación de conductas", ORIENTADO, "Orientado"),
        choice("orientacion_espacio", "Orientación · espacio", "Observación de conductas", ORIENTADO, "Orientado"),
        choice("orientacion_persona", "Orientación · persona", "Observación de conductas", ORIENTADO, "Orientado"),
        {"key": "nivel_intelectual", "label": "Nivel intelectual", "type": "text", "group": "Resultados", "default": "Normal promedio"},
        {"key": "visomotriz", "label": "Coordinación visomotriz", "type": "text", "group": "Resultados", "default": "Promedio"},
        {"key": "memoria", "label": "Nivel de memoria", "type": "text", "group": "Resultados", "default": "Memoria conservada"},
        {"key": "personalidad", "label": "Personalidad", "type": "textarea", "group": "Resultados", "wide": True},
        {"key": "afectividad", "label": "Afectividad", "type": "text", "group": "Resultados", "default": "Emocionalmente estable", "wide": True},
        {"key": "area_cognitiva", "label": "Área cognitiva", "type": "textarea", "group": "Conclusiones", "required": True, "wide": True},
        {"key": "area_emocional", "label": "Área emocional", "type": "textarea", "group": "Conclusiones", "required": True, "wide": True},
        choice("aptitud", "Resultado", "Conclusiones", opts("APTO", "APTO CON RESTRICCIONES", "NO APTO"), "APTO"),
        {"key": "recomendaciones", "label": "Recomendaciones", "type": "textarea", "group": "Conclusiones", "wide": True},
    ],
    "body": (
        """<table class="doc-grid">
<tr><td class="k">Postulante</td><td colspan="3">{{ paciente.nombre_completo }}</td></tr>
<tr><td class="k">Documento</td><td>{{ paciente.tipo_documento }} {{ paciente.documento }}</td>
    <td class="k">Edad</td><td>{{ paciente.edad }}</td></tr>
<tr><td class="k">Fecha de nacimiento</td><td>{{ paciente.fecha_nacimiento }}</td>
    <td class="k">Lugar de residencia</td><td>{{ campo.residencia }}</td></tr>
<tr><td class="k">Grado de instrucción</td><td>{{ campo.instruccion }}</td>
    <td class="k">Fecha de evaluación</td><td>{{ fecha.hoy }}</td></tr>
<tr><td class="k">Empresa</td><td>{{ campo.empresa }}</td>
    <td class="k">Puesto / tipo</td><td>{{ campo.puesto }} · {{ campo.tipo_evaluacion }}</td></tr>
</table>

<h2>Motivo de la evaluación</h2>
<p>{{ campo.motivo }}</p>

<h2>Observación de conductas</h2>
<table class="doc-grid">
<tr><td class="k">Presentación</td><td>{{ campo.presentacion }}</td>
    <td class="k">Postura</td><td>{{ campo.postura }}</td></tr>
<tr><td class="k">Discurso · ritmo</td><td>{{ campo.ritmo }}</td>
    <td class="k">Discurso · tono</td><td>{{ campo.tono }}</td></tr>
<tr><td class="k">Articulación</td><td colspan="3">{{ campo.articulacion }}</td></tr>
<tr><td class="k">Orientación</td><td colspan="3">Tiempo: {{ campo.orientacion_tiempo }} ·
    Espacio: {{ campo.orientacion_espacio }} · Persona: {{ campo.orientacion_persona }}</td></tr>
</table>

<h2>Resultados de la evaluación</h2>
<table class="doc-grid">
<tr><td class="k">Nivel intelectual</td><td>{{ campo.nivel_intelectual }}</td>
    <td class="k">Coordinación visomotriz</td><td>{{ campo.visomotriz }}</td></tr>
<tr><td class="k">Nivel de memoria</td><td colspan="3">{{ campo.memoria }}</td></tr>
<tr><td class="k">Personalidad</td><td colspan="3">{{ campo.personalidad|parrafos }}</td></tr>
<tr><td class="k">Afectividad</td><td colspan="3">{{ campo.afectividad }}</td></tr>
</table>

<h2>Conclusiones</h2>
<p><strong>Área cognitiva:</strong> {{ campo.area_cognitiva|parrafos }}</p>
<p><strong>Área emocional:</strong> {{ campo.area_emocional|parrafos }}</p>
<p>Resultado de la evaluación: <strong>{{ campo.aptitud }}</strong></p>

<h2>Recomendaciones</h2>
<p>{{ campo.recomendaciones|parrafos }}</p>"""
        + """<div class="doc-signatures">
<div class="sign"><div class="line"></div>
<div class="role">{{ profesional.nombre }}</div>
<div class="hint">Psicólogo(a) responsable · Col. {{ profesional.cmp }}</div></div>
</div>"""
    ),
}

_SRQ_ITEMS: tuple[tuple[str, str], ...] = (
    ("q1", "¿Tiene frecuentes dolores de cabeza?"),
    ("q2", "¿Tiene mal apetito?"),
    ("q3", "¿Duerme mal?"),
    ("q4", "¿Se asusta con facilidad?"),
    ("q5", "¿Sufre de temblor de manos?"),
    ("q6", "¿Se siente nervioso, tenso o aburrido?"),
    ("q7", "¿Sufre de mala digestión?"),
    ("q8", "¿No puede pensar con claridad?"),
    ("q9", "¿Se siente triste?"),
    ("q10", "¿Llora usted con mucha frecuencia?"),
    ("q11", "¿Tiene dificultad en disfrutar sus actividades diarias?"),
    ("q12", "¿Tiene dificultad para tomar decisiones?"),
    ("q13", "¿Tiene dificultad en hacer su trabajo y lo sufre?"),
    ("q14", "¿Es incapaz de desempeñar un papel útil en su vida?"),
    ("q15", "¿Ha perdido interés en las cosas?"),
    ("q16", "¿Siente que usted es una persona inútil?"),
    ("q17", "¿Ha tenido la idea de acabar con su vida?"),
    ("q18", "¿Se siente cansado todo el tiempo?"),
)

_SRQ_OPTIONS = [{"value": "0", "label": "No"}, {"value": "1", "label": "Sí"}]

_SRQ_ROWS = "".join(
    f"<tr><td>{number}. {label}</td><td>{{{{ campo.{key} }}}}</td></tr>"
    for number, (key, label) in enumerate(_SRQ_ITEMS, start=1)
)

TAMIZAJE_SRQ = {
    "code": "FIC-SRQ",
    "version": 1,
    "family": FICHA,
    "title": "Tamizaje de salud mental SRQ",
    "description": "Cuestionario de autorreporte de síntomas, 18 preguntas",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        *[
            {
                "key": key,
                "label": label,
                "type": "select",
                "group": "Últimos 30 días",
                "options": _SRQ_OPTIONS,
                "default": "0",
                "wide": True,
            }
            for key, label in _SRQ_ITEMS
        ],
        {
            "key": "puntaje_srq",
            "label": "Puntaje total",
            "type": "computed",
            "group": "Resultado",
            "sum": [key for key, _ in _SRQ_ITEMS],
            "help": "De 7 a más respuestas afirmativas orientan a un probable trastorno emocional.",
        },
        choice("resultado_srq", "Resultado del tamizaje", "Resultado",
               opts("Negativo", "Positivo"), "Negativo"),
        {"key": "interpretacion_srq", "label": "Interpretación y recomendaciones", "type": "textarea",
         "group": "Resultado", "required": True, "wide": True},
    ],
    "body": (
        HEADER_CLINICAL
        + """<p>Responda pensando en cómo se ha sentido durante los últimos treinta días.
Sus respuestas son confidenciales y no se comparten con terceros sin su autorización.</p>

<table class="doc-table">
<tr><th>Pregunta</th><th>Respuesta</th></tr>"""
        + _SRQ_ROWS
        + """</table>

<table class="doc-grid">
<tr><td class="k">Puntaje total</td><td><strong>{{ campo.puntaje_srq }} / 18</strong></td>
    <td class="k">Resultado</td><td>{{ campo.resultado_srq }}</td></tr>
</table>
<p class="doc-note">Cada respuesta afirmativa vale un punto. La pregunta 17, sobre ideas
de acabar con la vida, obliga a evaluación inmediata aunque el puntaje total sea bajo.</p>

<h2>Interpretación y recomendaciones</h2>
<p>{{ campo.interpretacion_srq|parrafos }}</p>"""
        + """<div class="doc-signatures">
<div class="sign"><div class="line"></div>
<div class="role">Psicólogo(a) responsable</div>
<div class="hint">{{ profesional.nombre }} · Colegiatura {{ profesional.cmp }}</div></div>
</div>"""
    ),
}

FICHA_TERAPIA_FISICA = {
    "code": "FIC-FIS",
    "version": 1,
    "family": FICHA,
    "title": "Ficha de evaluación de terapia física y rehabilitación",
    "description": "Evaluación postural, dolor, rango y fuerza muscular",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "ocupacion", "label": "Ocupación", "type": "text", "group": "Antecedentes"},
        {"key": "antecedentes", "label": "Antecedentes relevantes", "type": "text", "group": "Antecedentes",
         "placeholder": "Diabetes, hipertensión, patología coronaria, oncológica", "wide": True},
        {"key": "farmacos", "label": "Fármacos que recibe", "type": "text", "group": "Antecedentes", "wide": True},
        {"key": "motivo_terapia", "label": "Motivo de consulta", "type": "textarea", "group": "Anamnesis", "required": True, "wide": True},
        choice("postura_trabajo", "Postura predominante en el trabajo", "Anamnesis",
               opts("Sedente", "Bípedo", "Alternante"), "Sedente"),
        choice("movimientos_repetitivos", "Movimientos repetitivos", "Anamnesis", SI_NO, "No"),
        choice("carga_manual", "Manejo manual de carga", "Anamnesis", SI_NO, "No"),
        choice("cabeza", "Cabeza", "Evaluación postural", opts("Alineada", "Inclinada", "Rotada", "Adelantada"), "Alineada"),
        choice("hombros", "Hombros", "Evaluación postural", opts("Simétricos", "Descendido derecho", "Descendido izquierdo", "En anteposición"), "Simétricos"),
        choice("escapulas", "Escápulas", "Evaluación postural", opts("Simétricas", "Aladas"), "Simétricas"),
        choice("columna_cervical", "Columna cervical", "Evaluación postural", opts("Lordosis fisiológica", "Hiperlordosis", "Rectificada"), "Lordosis fisiológica"),
        choice("columna_dorsal", "Columna dorsal", "Evaluación postural", opts("Cifosis fisiológica", "Hipercifosis", "Plana"), "Cifosis fisiológica"),
        choice("columna_lumbar", "Columna lumbar", "Evaluación postural", opts("Lordosis fisiológica", "Hiperlordosis", "Rectificada"), "Lordosis fisiológica"),
        choice("escoliosis", "Escoliosis", "Evaluación postural", SI_NO, "No"),
        choice("pelvis", "Pelvis", "Evaluación postural", opts("Neutra", "Anteversión", "Retroversión"), "Neutra"),
        choice("rodillas", "Rodillas", "Evaluación postural", opts("Alineadas", "Genu valgo", "Genu varo", "Genu recurvatum"), "Alineadas"),
        choice("pies", "Pies", "Evaluación postural", opts("Alineados", "En eversión", "En inversión", "Pie plano"), "Alineados"),
        {"key": "zona_dolor", "label": "Zona del dolor", "type": "text", "group": "Dolor", "required": True, "wide": True},
        measure("eva", "Escala visual analógica (0 a 10)", "Dolor"),
        {"key": "tipo_dolor", "label": "Tipo de dolor", "type": "text", "group": "Dolor", "placeholder": "Punzante, urente, opresivo"},
        choice("irradiacion", "Irradiación", "Dolor", SI_NO, "No"),
        choice("apofisis", "Apófisis espinosas dolorosas a la palpación", "Examen físico", SI_NO, "No"),
        {"key": "tono_muscular", "label": "Tono muscular", "type": "text", "group": "Examen físico", "default": "Normotonía"},
        {"key": "rango_articular", "label": "Rango articular", "type": "text", "group": "Examen físico", "default": "Conservado", "wide": True},
        {"key": "fuerza_muscular", "label": "Fuerza muscular (escala de Daniels)", "type": "text", "group": "Examen físico", "default": "5/5", "wide": True},
        choice("lasegue", "Signo de Lasègue", "Maniobras", opts("Negativo", "Positivo derecho", "Positivo izquierdo", "Positivo bilateral"), "Negativo"),
        choice("bragard", "Signo de Bragard", "Maniobras", opts("Negativo", "Positivo derecho", "Positivo izquierdo", "Positivo bilateral"), "Negativo"),
        {"key": "diagnostico_fisio", "label": "Diagnóstico fisioterapéutico", "type": "textarea", "group": "Plan", "required": True, "wide": True},
        {"key": "plan_terapia", "label": "Plan de tratamiento y objetivos", "type": "textarea", "group": "Plan", "required": True, "wide": True},
        measure("sesiones", "Número de sesiones indicadas", "Plan"),
    ],
    "body": (
        HEADER_CLINICAL
        + """<table class="doc-grid">
<tr><td class="k">Ocupación</td><td>{{ campo.ocupacion }}</td>
    <td class="k">Fármacos</td><td>{{ campo.farmacos }}</td></tr>
<tr><td class="k">Antecedentes</td><td colspan="3">{{ campo.antecedentes }}</td></tr>
</table>

<h2>Anamnesis</h2>
<p>{{ campo.motivo_terapia|parrafos }}</p>
<table class="doc-grid">
<tr><td class="k">Postura laboral</td><td>{{ campo.postura_trabajo }}</td>
    <td class="k">Movimientos repetitivos</td><td>{{ campo.movimientos_repetitivos }}</td></tr>
<tr><td class="k">Manejo manual de carga</td><td colspan="3">{{ campo.carga_manual }}</td></tr>
</table>

<h2>Evaluación postural</h2>
<table class="doc-table">
<tr><th>Segmento</th><th>Hallazgo</th><th>Segmento</th><th>Hallazgo</th></tr>
<tr><td>Cabeza</td><td>{{ campo.cabeza }}</td><td>Hombros</td><td>{{ campo.hombros }}</td></tr>
<tr><td>Escápulas</td><td>{{ campo.escapulas }}</td><td>Escoliosis</td><td>{{ campo.escoliosis }}</td></tr>
<tr><td>Columna cervical</td><td>{{ campo.columna_cervical }}</td><td>Columna dorsal</td><td>{{ campo.columna_dorsal }}</td></tr>
<tr><td>Columna lumbar</td><td>{{ campo.columna_lumbar }}</td><td>Pelvis</td><td>{{ campo.pelvis }}</td></tr>
<tr><td>Rodillas</td><td>{{ campo.rodillas }}</td><td>Pies</td><td>{{ campo.pies }}</td></tr>
</table>

<h2>Dolor</h2>
<table class="doc-grid">
<tr><td class="k">Zona</td><td>{{ campo.zona_dolor }}</td>
    <td class="k">EVA</td><td>{{ campo.eva }} / 10</td></tr>
<tr><td class="k">Tipo</td><td>{{ campo.tipo_dolor }}</td>
    <td class="k">Irradiación</td><td>{{ campo.irradiacion }}</td></tr>
</table>

<h2>Examen físico</h2>
<table class="doc-grid">
<tr><td class="k">Apófisis espinosas</td><td>{{ campo.apofisis }}</td>
    <td class="k">Tono muscular</td><td>{{ campo.tono_muscular }}</td></tr>
<tr><td class="k">Rango articular</td><td>{{ campo.rango_articular }}</td>
    <td class="k">Fuerza muscular</td><td>{{ campo.fuerza_muscular }}</td></tr>
<tr><td class="k">Signo de Lasègue</td><td>{{ campo.lasegue }}</td>
    <td class="k">Signo de Bragard</td><td>{{ campo.bragard }}</td></tr>
</table>

<h2>Diagnóstico fisioterapéutico</h2>
<p>{{ campo.diagnostico_fisio|parrafos }}</p>

<h2>Plan de tratamiento</h2>
<p>{{ campo.plan_terapia|parrafos }}</p>
<p><strong>Sesiones indicadas:</strong> {{ campo.sesiones }}</p>"""
        + """<div class="doc-signatures">
<div class="sign"><div class="line"></div>
<div class="role">Fisioterapeuta responsable</div>
<div class="hint">{{ profesional.nombre }} · Colegiatura {{ profesional.cmp }}</div></div>
</div>"""
    ),
}

CONTROL_TERAPIA = {
    "code": "FIC-TER",
    "version": 1,
    "family": FICHA,
    "title": "Hoja de control de sesiones de terapia física",
    "description": "Agentes aplicados, evolución del dolor y asistencia",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "diagnostico_terapia", "label": "Diagnóstico", "type": "text", "group": "Sesión", "required": True, "wide": True},
        measure("numero_sesion", "Número de sesión", "Sesión"),
        measure("sesiones_indicadas", "Sesiones indicadas", "Sesión"),
        measure("eva_inicio", "EVA al inicio de la sesión (0 a 10)", "Evolución del dolor"),
        measure("eva_final", "EVA al término de la sesión (0 a 10)", "Evolución del dolor"),
        choice("compresas", "Compresas húmedo calientes o frías", "Agentes aplicados", SI_NO, "No"),
        choice("ultrasonido", "Ultrasonido terapéutico", "Agentes aplicados", SI_NO, "No"),
        choice("electroterapia", "Electroterapia (TENS o corrientes)", "Agentes aplicados", SI_NO, "No"),
        choice("magnetoterapia", "Magnetoterapia", "Agentes aplicados", SI_NO, "No"),
        choice("laser", "Laserterapia", "Agentes aplicados", SI_NO, "No"),
        choice("masoterapia", "Masoterapia o terapia manual", "Agentes aplicados", SI_NO, "No"),
        choice("cinesiterapia", "Cinesiterapia y ejercicios", "Agentes aplicados", SI_NO, "No"),
        {"key": "zona_tratada", "label": "Zona tratada", "type": "text", "group": "Agentes aplicados", "wide": True},
        {"key": "evolucion", "label": "Evolución y tolerancia", "type": "textarea", "group": "Evolución", "required": True, "wide": True},
        {"key": "indicaciones_casa", "label": "Indicaciones para el domicilio", "type": "textarea", "group": "Evolución", "wide": True},
        {"key": "proxima_sesion", "label": "Próxima sesión", "type": "date", "group": "Evolución"},
    ],
    "body": (
        HEADER_CLINICAL
        + """<table class="doc-grid">
<tr><td class="k">Diagnóstico</td><td colspan="3">{{ campo.diagnostico_terapia }}</td></tr>
<tr><td class="k">Sesión</td><td>{{ campo.numero_sesion }} de {{ campo.sesiones_indicadas }}</td>
    <td class="k">Zona tratada</td><td>{{ campo.zona_tratada }}</td></tr>
</table>

<h2>Agentes aplicados</h2>
<table class="doc-table">
<tr><th>Agente</th><th>Aplicado</th><th>Agente</th><th>Aplicado</th></tr>
<tr><td>Compresas</td><td>{{ campo.compresas }}</td><td>Ultrasonido</td><td>{{ campo.ultrasonido }}</td></tr>
<tr><td>Electroterapia</td><td>{{ campo.electroterapia }}</td><td>Magnetoterapia</td><td>{{ campo.magnetoterapia }}</td></tr>
<tr><td>Laserterapia</td><td>{{ campo.laser }}</td><td>Masoterapia</td><td>{{ campo.masoterapia }}</td></tr>
<tr><td>Cinesiterapia</td><td>{{ campo.cinesiterapia }}</td><td></td><td></td></tr>
</table>

<h2>Evolución</h2>
<table class="doc-grid">
<tr><td class="k">EVA al inicio</td><td>{{ campo.eva_inicio }} / 10</td>
    <td class="k">EVA al término</td><td>{{ campo.eva_final }} / 10</td></tr>
<tr><td class="k">Próxima sesión</td><td colspan="3">{{ campo.proxima_sesion }}</td></tr>
</table>
<p>{{ campo.evolucion|parrafos }}</p>
<p><strong>Indicaciones para el domicilio:</strong> {{ campo.indicaciones_casa|parrafos }}</p>"""
        + """<div class="doc-signatures">
<div class="sign"><div class="line"></div>
<div class="role">Fisioterapeuta</div>
<div class="hint">{{ profesional.nombre }} · Colegiatura {{ profesional.cmp }}</div></div>
<div class="sign"><div class="line"></div><div class="role">Firma del paciente</div>
<div class="hint">{{ paciente.nombre_completo }}</div></div>
</div>"""
    ),
}

HISTORIA_RECIEN_NACIDO = {
    "code": "FIC-RN",
    "version": 1,
    "family": FICHA,
    "title": "Historia clínica del recién nacido",
    "description": "Datos del parto, Apgar, Capurro y antropometría",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "madre", "label": "Nombre de la madre", "type": "text", "group": "Parto", "required": True, "wide": True},
        {"key": "hora_nacimiento", "label": "Hora de nacimiento", "type": "text", "group": "Parto", "placeholder": "14:35"},
        choice("tipo_parto", "Tipo de parto", "Parto", opts("Vaginal", "Cesárea"), "Vaginal"),
        choice("presentacion", "Presentación", "Parto", opts("Cefálica", "Podálica", "Transversa"), "Cefálica"),
        choice("liquido_amniotico", "Líquido amniótico", "Parto",
               opts("Claro", "Meconial", "Sanguinolento"), "Claro"),
        measure("edad_gestacional_rn", "Edad gestacional por Capurro (semanas)", "Parto"),
        choice("sexo_rn", "Sexo", "Antropometría", opts("Femenino", "Masculino"), "Femenino"),
        measure("peso_rn", "Peso (gramos)", "Antropometría"),
        measure("talla_rn", "Talla (cm)", "Antropometría"),
        measure("perimetro_cefalico", "Perímetro cefálico (cm)", "Antropometría"),
        measure("perimetro_toracico", "Perímetro torácico (cm)", "Antropometría"),
        measure("perimetro_abdominal", "Perímetro abdominal (cm)", "Antropometría"),
        measure("apgar_1", "Apgar al minuto", "Apgar"),
        measure("apgar_5", "Apgar a los cinco minutos", "Apgar"),
        choice("reanimacion", "Requirió reanimación", "Apgar", SI_NO, "No"),
        choice("examen_fisico_rn", "Examen físico general", "Atención inmediata",
               opts("Sin alteraciones aparentes", "Con hallazgos"), "Sin alteraciones aparentes"),
        choice("vitamina_k", "Vitamina K aplicada", "Atención inmediata", SI_NO, "Sí"),
        choice("profilaxis_ocular", "Profilaxis ocular aplicada", "Atención inmediata", SI_NO, "Sí"),
        choice("contacto_piel", "Contacto piel a piel y lactancia precoz", "Atención inmediata", SI_NO, "Sí"),
        choice("vacuna_bcg", "Vacuna BCG", "Atención inmediata", SI_NO, "No"),
        choice("vacuna_hvb", "Vacuna contra la hepatitis B", "Atención inmediata", SI_NO, "No"),
        {"key": "hallazgos_rn", "label": "Hallazgos y observaciones", "type": "textarea", "group": "Atención inmediata", "default": "Ninguno", "wide": True},
        {"key": "diagnostico_rn", "label": "Diagnóstico del recién nacido", "type": "textarea", "group": "Conclusión", "required": True, "wide": True},
    ],
    "body": (
        HEADER_CLINICAL
        + """<h2>Datos del parto</h2>
<table class="doc-grid">
<tr><td class="k">Madre</td><td colspan="3">{{ campo.madre }}</td></tr>
<tr><td class="k">Hora de nacimiento</td><td>{{ campo.hora_nacimiento }}</td>
    <td class="k">Tipo de parto</td><td>{{ campo.tipo_parto }}</td></tr>
<tr><td class="k">Presentación</td><td>{{ campo.presentacion }}</td>
    <td class="k">Líquido amniótico</td><td>{{ campo.liquido_amniotico }}</td></tr>
<tr><td class="k">Edad gestacional</td><td>{{ campo.edad_gestacional_rn }} semanas por Capurro</td>
    <td class="k">Sexo</td><td>{{ campo.sexo_rn }}</td></tr>
</table>

<h2>Antropometría</h2>
<table class="doc-table">
<tr><th>Peso</th><th>Talla</th><th>P. cefálico</th><th>P. torácico</th><th>P. abdominal</th></tr>
<tr><td>{{ campo.peso_rn }} g</td><td>{{ campo.talla_rn }} cm</td><td>{{ campo.perimetro_cefalico }} cm</td>
    <td>{{ campo.perimetro_toracico }} cm</td><td>{{ campo.perimetro_abdominal }} cm</td></tr>
</table>

<h2>Apgar</h2>
<table class="doc-grid">
<tr><td class="k">Al minuto</td><td>{{ campo.apgar_1 }} / 10</td>
    <td class="k">A los cinco minutos</td><td>{{ campo.apgar_5 }} / 10</td></tr>
<tr><td class="k">Requirió reanimación</td><td colspan="3">{{ campo.reanimacion }}</td></tr>
</table>

<h2>Atención inmediata</h2>
<table class="doc-grid">
<tr><td class="k">Examen físico</td><td>{{ campo.examen_fisico_rn }}</td>
    <td class="k">Vitamina K</td><td>{{ campo.vitamina_k }}</td></tr>
<tr><td class="k">Profilaxis ocular</td><td>{{ campo.profilaxis_ocular }}</td>
    <td class="k">Contacto piel a piel</td><td>{{ campo.contacto_piel }}</td></tr>
<tr><td class="k">Vacuna BCG</td><td>{{ campo.vacuna_bcg }}</td>
    <td class="k">Vacuna hepatitis B</td><td>{{ campo.vacuna_hvb }}</td></tr>
</table>
<p><strong>Hallazgos y observaciones:</strong> {{ campo.hallazgos_rn|parrafos }}</p>

<h2>Diagnóstico</h2>
<p>{{ campo.diagnostico_rn|parrafos }}</p>"""
        + SIGN_DOCTOR
    ),
}

HISTORIA_CLINICA_GENERAL = {
    "code": "FIC-HCG",
    "version": 1,
    "family": FICHA,
    "title": "Historia clínica general",
    "description": "Anamnesis, funciones vitales, examen físico, diagnóstico y plan",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "motivo_consulta", "label": "Motivo de consulta", "type": "text", "group": "Anamnesis", "required": True, "wide": True},
        {"key": "enfermedad_actual", "label": "Enfermedad actual", "type": "textarea", "group": "Anamnesis", "required": True, "wide": True},
        measure("tiempo_enfermedad", "Tiempo de enfermedad (días)", "Anamnesis"),
        choice("forma_inicio", "Forma de inicio", "Anamnesis", opts("Insidioso", "Brusco"), "Insidioso"),
        choice("curso", "Curso", "Anamnesis", opts("Progresivo", "Estacionario", "Remitente"), "Progresivo"),
        {"key": "antecedentes_personales", "label": "Antecedentes personales", "type": "textarea", "group": "Antecedentes", "default": "Niega", "wide": True},
        {"key": "antecedentes_familiares", "label": "Antecedentes familiares", "type": "textarea", "group": "Antecedentes", "default": "Niega", "wide": True},
        {"key": "alergias_hc", "label": "Alergias referidas", "type": "text", "group": "Antecedentes", "default": "Niega", "wide": True},
        {"key": "medicacion_habitual", "label": "Medicación habitual", "type": "text", "group": "Antecedentes", "default": "Ninguna", "wide": True},
        {"key": "pa", "label": "Presión arterial (mmHg)", "type": "text", "group": "Funciones vitales", "placeholder": "120/80"},
        measure("fc", "Frecuencia cardíaca (lpm)", "Funciones vitales"),
        measure("fr", "Frecuencia respiratoria (rpm)", "Funciones vitales"),
        measure("temperatura", "Temperatura (°C)", "Funciones vitales"),
        measure("saturacion", "Saturación de oxígeno (%)", "Funciones vitales"),
        measure("peso_hc", "Peso (kg)", "Funciones vitales"),
        measure("talla_hc", "Talla (cm)", "Funciones vitales"),
        choice("estado_general", "Estado general", "Examen físico",
               opts("Bueno", "Regular", "Malo"), "Bueno"),
        {"key": "piel_tcsc", "label": "Piel y tejido celular subcutáneo", "type": "text", "group": "Examen físico", "default": "Sin alteraciones", "wide": True},
        {"key": "cabeza_cuello", "label": "Cabeza y cuello", "type": "text", "group": "Examen físico", "default": "Sin alteraciones", "wide": True},
        {"key": "torax_pulmones", "label": "Tórax y pulmones", "type": "text", "group": "Examen físico", "default": "Murmullo vesicular pasa bien en ambos campos pulmonares", "wide": True},
        {"key": "cardiovascular", "label": "Cardiovascular", "type": "text", "group": "Examen físico", "default": "Ruidos cardíacos rítmicos, no soplos", "wide": True},
        {"key": "abdomen", "label": "Abdomen", "type": "text", "group": "Examen físico", "default": "Blando, depresible, no doloroso a la palpación", "wide": True},
        {"key": "genitourinario", "label": "Genitourinario", "type": "text", "group": "Examen físico", "default": "Puño percusión lumbar negativa", "wide": True},
        {"key": "neurologico", "label": "Neurológico", "type": "text", "group": "Examen físico", "default": "Despierto, orientado en tiempo, espacio y persona", "wide": True},
        {"key": "diagnosticos_hc", "label": "Diagnósticos presuntivos", "type": "textarea", "group": "Diagnóstico y plan", "required": True, "wide": True},
        {"key": "cie10_hc", "label": "CIE-10", "type": "text", "group": "Diagnóstico y plan", "placeholder": "J00"},
        {"key": "examenes", "label": "Exámenes auxiliares solicitados", "type": "textarea", "group": "Diagnóstico y plan", "default": "Ninguno", "wide": True},
        {"key": "plan_hc", "label": "Plan de trabajo e indicaciones", "type": "textarea", "group": "Diagnóstico y plan", "required": True, "wide": True},
    ],
    "body": (
        HEADER_CLINICAL
        + """<h2>Anamnesis</h2>
<table class="doc-grid">
<tr><td class="k">Motivo de consulta</td><td colspan="3">{{ campo.motivo_consulta }}</td></tr>
<tr><td class="k">Tiempo de enfermedad</td><td>{{ campo.tiempo_enfermedad }} días</td>
    <td class="k">Inicio y curso</td><td>{{ campo.forma_inicio }} · {{ campo.curso }}</td></tr>
</table>
<p>{{ campo.enfermedad_actual|parrafos }}</p>

<h2>Antecedentes</h2>
<table class="doc-grid">
<tr><td class="k">Personales</td><td colspan="3">{{ campo.antecedentes_personales }}</td></tr>
<tr><td class="k">Familiares</td><td colspan="3">{{ campo.antecedentes_familiares }}</td></tr>
<tr><td class="k">Alergias</td><td>{{ campo.alergias_hc }}</td>
    <td class="k">Medicación habitual</td><td>{{ campo.medicacion_habitual }}</td></tr>
</table>

<h2>Funciones vitales</h2>
<table class="doc-table">
<tr><th>PA</th><th>FC</th><th>FR</th><th>T°</th><th>SatO₂</th><th>Peso</th><th>Talla</th></tr>
<tr><td>{{ campo.pa }}</td><td>{{ campo.fc }}</td><td>{{ campo.fr }}</td><td>{{ campo.temperatura }}</td>
    <td>{{ campo.saturacion }} %</td><td>{{ campo.peso_hc }} kg</td><td>{{ campo.talla_hc }} cm</td></tr>
</table>

<h2>Examen físico</h2>
<table class="doc-grid">
<tr><td class="k">Estado general</td><td colspan="3">{{ campo.estado_general }}</td></tr>
<tr><td class="k">Piel y TCSC</td><td colspan="3">{{ campo.piel_tcsc }}</td></tr>
<tr><td class="k">Cabeza y cuello</td><td colspan="3">{{ campo.cabeza_cuello }}</td></tr>
<tr><td class="k">Tórax y pulmones</td><td colspan="3">{{ campo.torax_pulmones }}</td></tr>
<tr><td class="k">Cardiovascular</td><td colspan="3">{{ campo.cardiovascular }}</td></tr>
<tr><td class="k">Abdomen</td><td colspan="3">{{ campo.abdomen }}</td></tr>
<tr><td class="k">Genitourinario</td><td colspan="3">{{ campo.genitourinario }}</td></tr>
<tr><td class="k">Neurológico</td><td colspan="3">{{ campo.neurologico }}</td></tr>
</table>

<h2>Diagnóstico</h2>
<p>{{ campo.diagnosticos_hc|parrafos }}</p>
<p><strong>CIE-10:</strong> {{ campo.cie10_hc }}</p>

<h2>Exámenes auxiliares</h2>
<p>{{ campo.examenes|parrafos }}</p>

<h2>Plan de trabajo</h2>
<p>{{ campo.plan_hc|parrafos }}</p>"""
        + SIGN_DOCTOR
    ),
}

# La versión 2 incorpora los cuatro campos que el formato en papel de la clínica
# (hoja «H.C.Asistencial») tiene y la primera versión no recogía: las
# intervenciones quirúrgicas, la ectoscopía y, dentro del examen físico, el
# sistema osteomuscular y el cajón de otros hallazgos. El orden del examen sigue
# al de la hoja impresa, que es el que el personal ya tiene memorizado.
HISTORIA_CLINICA_GENERAL_V2 = {
    "code": "FIC-HCG",
    "version": 2,
    "family": FICHA,
    "title": "Historia clínica general",
    "description": "Anamnesis, antecedentes, funciones vitales, ectoscopía, examen físico, diagnóstico y plan",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "motivo_consulta", "label": "Motivo de consulta", "type": "text", "group": "Anamnesis", "required": True, "wide": True},
        {"key": "enfermedad_actual", "label": "Enfermedad actual", "type": "textarea", "group": "Anamnesis", "required": True, "wide": True},
        measure("tiempo_enfermedad", "Tiempo de enfermedad (días)", "Anamnesis"),
        choice("forma_inicio", "Forma de inicio", "Anamnesis", opts("Insidioso", "Brusco"), "Insidioso"),
        choice("curso", "Curso", "Anamnesis", opts("Progresivo", "Estacionario", "Remitente"), "Progresivo"),
        {"key": "antecedentes_personales", "label": "Antecedentes personales", "type": "textarea", "group": "Antecedentes", "default": "Niega", "wide": True},
        {"key": "antecedentes_familiares", "label": "Antecedentes familiares", "type": "textarea", "group": "Antecedentes", "default": "Niega", "wide": True},
        {"key": "intervenciones_qx", "label": "Intervenciones quirúrgicas", "type": "text", "group": "Antecedentes", "default": "Niega", "wide": True},
        {"key": "alergias_hc", "label": "Alergias referidas", "type": "text", "group": "Antecedentes", "default": "Niega", "wide": True},
        {"key": "medicacion_habitual", "label": "Medicación habitual", "type": "text", "group": "Antecedentes", "default": "Ninguna", "wide": True},
        {"key": "pa", "label": "Presión arterial (mmHg)", "type": "text", "group": "Funciones vitales", "placeholder": "120/80"},
        measure("fc", "Frecuencia cardíaca (lpm)", "Funciones vitales"),
        measure("fr", "Frecuencia respiratoria (rpm)", "Funciones vitales"),
        measure("temperatura", "Temperatura (°C)", "Funciones vitales"),
        measure("saturacion", "Saturación de oxígeno (%)", "Funciones vitales"),
        measure("peso_hc", "Peso (kg)", "Funciones vitales"),
        measure("talla_hc", "Talla (cm)", "Funciones vitales"),
        {"key": "ectoscopia", "label": "Ectoscopía", "type": "text", "group": "Examen físico", "default": "Aparente buen estado general, de hidratación y nutrición; lúcido y orientado", "wide": True},
        choice("estado_general", "Estado general", "Examen físico",
               opts("Bueno", "Regular", "Malo"), "Bueno"),
        {"key": "piel_tcsc", "label": "Piel y tejido celular subcutáneo", "type": "text", "group": "Examen físico", "default": "Sin alteraciones", "wide": True},
        {"key": "osteomuscular", "label": "Sistema osteomuscular · movilidad activa y pasiva", "type": "text", "group": "Examen físico", "default": "Conservadas, sin limitación funcional", "wide": True},
        {"key": "cabeza_cuello", "label": "Cabeza y cuello", "type": "text", "group": "Examen físico", "default": "Sin alteraciones", "wide": True},
        {"key": "torax_pulmones", "label": "Tórax y pulmones", "type": "text", "group": "Examen físico", "default": "Murmullo vesicular pasa bien en ambos campos pulmonares", "wide": True},
        {"key": "cardiovascular", "label": "Cardiovascular", "type": "text", "group": "Examen físico", "default": "Ruidos cardíacos rítmicos, no soplos", "wide": True},
        {"key": "abdomen", "label": "Abdomen", "type": "text", "group": "Examen físico", "default": "Blando, depresible, no doloroso a la palpación", "wide": True},
        {"key": "genitourinario", "label": "Genitourinario", "type": "text", "group": "Examen físico", "default": "Puño percusión lumbar negativa", "wide": True},
        {"key": "neurologico", "label": "Neurológico", "type": "text", "group": "Examen físico", "default": "Despierto, orientado en tiempo, espacio y persona", "wide": True},
        {"key": "otros_examen", "label": "Otros hallazgos", "type": "textarea", "group": "Examen físico", "default": "Ninguno", "wide": True},
        {"key": "diagnosticos_hc", "label": "Diagnósticos presuntivos", "type": "textarea", "group": "Diagnóstico y plan", "required": True, "wide": True},
        {"key": "cie10_hc", "label": "CIE-10", "type": "text", "group": "Diagnóstico y plan", "placeholder": "J00"},
        {"key": "examenes", "label": "Exámenes auxiliares solicitados", "type": "textarea", "group": "Diagnóstico y plan", "default": "Ninguno", "wide": True},
        {"key": "plan_hc", "label": "Plan de trabajo e indicaciones", "type": "textarea", "group": "Diagnóstico y plan", "required": True, "wide": True},
    ],
    "body": (
        HEADER_CLINICAL
        + """<h2>Filiación</h2>
<table class="doc-grid">
<tr><td class="k">Fecha de nacimiento</td><td>{{ paciente.fecha_nacimiento }}</td>
    <td class="k">Lugar de nacimiento</td><td>{{ paciente.lugar_nacimiento }}</td></tr>
<tr><td class="k">Sexo</td><td>{{ paciente.sexo }}</td>
    <td class="k">Estado civil</td><td>{{ paciente.estado_civil }}</td></tr>
<tr><td class="k">Ocupación</td><td>{{ paciente.ocupacion }}</td>
    <td class="k">Domicilio</td><td>{{ paciente.direccion }}</td></tr>
</table>

<h2>Anamnesis</h2>
<table class="doc-grid">
<tr><td class="k">Motivo de consulta</td><td colspan="3">{{ campo.motivo_consulta }}</td></tr>
<tr><td class="k">Tiempo de enfermedad</td><td>{{ campo.tiempo_enfermedad }} días</td>
    <td class="k">Inicio y curso</td><td>{{ campo.forma_inicio }} · {{ campo.curso }}</td></tr>
</table>
<p>{{ campo.enfermedad_actual|parrafos }}</p>

<h2>Antecedentes</h2>
<table class="doc-grid">
<tr><td class="k">Personales</td><td colspan="3">{{ campo.antecedentes_personales }}</td></tr>
<tr><td class="k">Familiares</td><td colspan="3">{{ campo.antecedentes_familiares }}</td></tr>
<tr><td class="k">Intervenciones quirúrgicas</td><td colspan="3">{{ campo.intervenciones_qx }}</td></tr>
<tr><td class="k">Alergias</td><td>{{ campo.alergias_hc }}</td>
    <td class="k">Medicación habitual</td><td>{{ campo.medicacion_habitual }}</td></tr>
</table>

<h2>Funciones vitales</h2>
<table class="doc-table">
<tr><th>PA</th><th>FC</th><th>FR</th><th>T°</th><th>SatO₂</th><th>Peso</th><th>Talla</th></tr>
<tr><td>{{ campo.pa }}</td><td>{{ campo.fc }}</td><td>{{ campo.fr }}</td><td>{{ campo.temperatura }}</td>
    <td>{{ campo.saturacion }} %</td><td>{{ campo.peso_hc }} kg</td><td>{{ campo.talla_hc }} cm</td></tr>
</table>

<h2>Ectoscopía</h2>
<p>{{ campo.ectoscopia }}</p>

<h2>Examen físico</h2>
<table class="doc-grid">
<tr><td class="k">Estado general</td><td colspan="3">{{ campo.estado_general }}</td></tr>
<tr><td class="k">Piel y TCSC</td><td colspan="3">{{ campo.piel_tcsc }}</td></tr>
<tr><td class="k">Sistema osteomuscular</td><td colspan="3">{{ campo.osteomuscular }}</td></tr>
<tr><td class="k">Cabeza y cuello</td><td colspan="3">{{ campo.cabeza_cuello }}</td></tr>
<tr><td class="k">Tórax y pulmones</td><td colspan="3">{{ campo.torax_pulmones }}</td></tr>
<tr><td class="k">Cardiovascular</td><td colspan="3">{{ campo.cardiovascular }}</td></tr>
<tr><td class="k">Abdomen</td><td colspan="3">{{ campo.abdomen }}</td></tr>
<tr><td class="k">Genitourinario</td><td colspan="3">{{ campo.genitourinario }}</td></tr>
<tr><td class="k">Neurológico</td><td colspan="3">{{ campo.neurologico }}</td></tr>
</table>
<p><strong>Otros hallazgos:</strong> {{ campo.otros_examen|parrafos }}</p>

<h2>Diagnóstico</h2>
<p>{{ campo.diagnosticos_hc|parrafos }}</p>
<p><strong>CIE-10:</strong> {{ campo.cie10_hc }}</p>

<h2>Exámenes auxiliares</h2>
<p>{{ campo.examenes|parrafos }}</p>

<h2>Plan de trabajo</h2>
<p>{{ campo.plan_hc|parrafos }}</p>"""
        + SIGN_DOCTOR
    ),
}


EVOLUCION_HOSPITALIZACION = {
    "code": "FIC-HOS",
    "version": 1,
    "family": FICHA,
    "title": "Hoja de evolución del paciente hospitalizado",
    "description": "Evolución diaria, funciones vitales, balance e indicaciones",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        measure("dia_hospitalizacion", "Día de hospitalización", "Ingreso"),
        {"key": "cama", "label": "Cama", "type": "text", "group": "Ingreso"},
        {"key": "diagnostico_hosp", "label": "Diagnóstico", "type": "text", "group": "Ingreso", "required": True, "wide": True},
        {"key": "pa_hosp", "label": "Presión arterial (mmHg)", "type": "text", "group": "Funciones vitales", "placeholder": "120/80"},
        measure("fc_hosp", "Frecuencia cardíaca (lpm)", "Funciones vitales"),
        measure("fr_hosp", "Frecuencia respiratoria (rpm)", "Funciones vitales"),
        measure("temperatura_hosp", "Temperatura (°C)", "Funciones vitales"),
        measure("saturacion_hosp", "Saturación de oxígeno (%)", "Funciones vitales"),
        measure("diuresis", "Diuresis de 24 horas (mL)", "Balance"),
        measure("ingresos", "Ingresos de 24 horas (mL)", "Balance"),
        measure("egresos", "Egresos de 24 horas (mL)", "Balance"),
        choice("via_periferica", "Vía periférica permeable", "Balance", SI_NO, "Sí"),
        {"key": "subjetivo", "label": "Refiere el paciente", "type": "textarea", "group": "Evolución", "required": True, "wide": True},
        {"key": "objetivo", "label": "Al examen físico", "type": "textarea", "group": "Evolución", "required": True, "wide": True},
        {"key": "apreciacion", "label": "Apreciación", "type": "textarea", "group": "Evolución", "wide": True},
        {"key": "indicaciones_hosp", "label": "Indicaciones del día", "type": "textarea", "group": "Evolución", "required": True, "wide": True},
    ],
    "body": (
        HEADER_CLINICAL
        + """<table class="doc-grid">
<tr><td class="k">Día de hospitalización</td><td>{{ campo.dia_hospitalizacion }}</td>
    <td class="k">Cama</td><td>{{ campo.cama }}</td></tr>
<tr><td class="k">Diagnóstico</td><td colspan="3">{{ campo.diagnostico_hosp }}</td></tr>
</table>

<h2>Funciones vitales y balance</h2>
<table class="doc-table">
<tr><th>PA</th><th>FC</th><th>FR</th><th>T°</th><th>SatO₂</th><th>Diuresis</th></tr>
<tr><td>{{ campo.pa_hosp }}</td><td>{{ campo.fc_hosp }}</td><td>{{ campo.fr_hosp }}</td>
    <td>{{ campo.temperatura_hosp }}</td><td>{{ campo.saturacion_hosp }} %</td><td>{{ campo.diuresis }} mL</td></tr>
</table>
<table class="doc-grid">
<tr><td class="k">Ingresos 24 h</td><td>{{ campo.ingresos }} mL</td>
    <td class="k">Egresos 24 h</td><td>{{ campo.egresos }} mL</td></tr>
<tr><td class="k">Vía periférica</td><td colspan="3">{{ campo.via_periferica }}</td></tr>
</table>

<h2>Evolución</h2>
<p><strong>Refiere:</strong> {{ campo.subjetivo|parrafos }}</p>
<p><strong>Al examen:</strong> {{ campo.objetivo|parrafos }}</p>
<p><strong>Apreciación:</strong> {{ campo.apreciacion|parrafos }}</p>

<h2>Indicaciones</h2>
<p>{{ campo.indicaciones_hosp|parrafos }}</p>"""
        + SIGN_DOCTOR
    ),
}

REPORTE_OPERATORIO = {
    "code": "FIC-OPE",
    "version": 1,
    "family": FICHA,
    "title": "Reporte operatorio",
    "description": "Equipo quirúrgico, diagnósticos, técnica, hallazgos y destino",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "cirujano", "label": "Cirujano principal", "type": "text", "group": "Equipo", "required": True, "wide": True},
        {"key": "ayudante1", "label": "Primer ayudante", "type": "text", "group": "Equipo"},
        {"key": "ayudante2", "label": "Segundo ayudante", "type": "text", "group": "Equipo"},
        {"key": "instrumentista", "label": "Instrumentista", "type": "text", "group": "Equipo"},
        {"key": "circulante", "label": "Circulante", "type": "text", "group": "Equipo"},
        {"key": "anestesiologo", "label": "Anestesiólogo", "type": "text", "group": "Equipo"},
        choice("tipo_anestesia", "Tipo de anestesia", "Equipo",
               opts("Local", "Regional", "Raquídea", "General"), "Local"),
        choice("tipo_cirugia", "Tipo de cirugía", "Acto quirúrgico", opts("Electiva", "Emergencia"), "Electiva"),
        {"key": "hora_inicio", "label": "Hora de inicio", "type": "text", "group": "Acto quirúrgico", "placeholder": "09:15"},
        {"key": "hora_termino", "label": "Hora de término", "type": "text", "group": "Acto quirúrgico", "placeholder": "10:40"},
        {"key": "tiempo_operatorio", "label": "Tiempo operatorio", "type": "text", "group": "Acto quirúrgico", "placeholder": "1 hora 25 minutos"},
        {"key": "dx_preoperatorio", "label": "Diagnóstico preoperatorio", "type": "textarea", "group": "Diagnósticos", "required": True, "wide": True},
        {"key": "dx_postoperatorio", "label": "Diagnóstico postoperatorio", "type": "textarea", "group": "Diagnósticos", "required": True, "wide": True},
        {"key": "cirugia_programada", "label": "Cirugía programada", "type": "text", "group": "Procedimiento", "required": True, "wide": True},
        {"key": "cirugia_realizada", "label": "Cirugía realizada", "type": "text", "group": "Procedimiento", "required": True, "wide": True},
        {"key": "tecnica", "label": "Descripción de la técnica quirúrgica", "type": "textarea", "group": "Procedimiento", "required": True, "wide": True},
        {"key": "hallazgos_qx", "label": "Hallazgos", "type": "textarea", "group": "Procedimiento", "required": True, "wide": True},
        {"key": "incidentes", "label": "Incidentes y accidentes", "type": "textarea", "group": "Procedimiento", "default": "Ninguno", "wide": True},
        {"key": "complicaciones", "label": "Complicaciones", "type": "textarea", "group": "Procedimiento", "default": "Ninguna", "wide": True},
        choice("anatomia_patologica", "Envío a anatomía patológica", "Cierre", SI_NO, "No"),
        measure("piezas", "Número de piezas enviadas", "Cierre"),
        choice("implantes", "Uso de implantes", "Cierre", SI_NO, "No"),
        choice("destino", "Destino del paciente", "Cierre",
               opts("Recuperación", "Hospitalización", "Alta el mismo día", "Referido"), "Recuperación"),
    ],
    "body": (
        HEADER_CLINICAL
        + """<h2>Equipo quirúrgico</h2>
<table class="doc-grid">
<tr><td class="k">Cirujano principal</td><td colspan="3">{{ campo.cirujano }}</td></tr>
<tr><td class="k">Primer ayudante</td><td>{{ campo.ayudante1 }}</td>
    <td class="k">Segundo ayudante</td><td>{{ campo.ayudante2 }}</td></tr>
<tr><td class="k">Instrumentista</td><td>{{ campo.instrumentista }}</td>
    <td class="k">Circulante</td><td>{{ campo.circulante }}</td></tr>
<tr><td class="k">Anestesiólogo</td><td>{{ campo.anestesiologo }}</td>
    <td class="k">Tipo de anestesia</td><td>{{ campo.tipo_anestesia }}</td></tr>
<tr><td class="k">Tipo de cirugía</td><td>{{ campo.tipo_cirugia }}</td>
    <td class="k">Tiempo operatorio</td><td>{{ campo.tiempo_operatorio }}</td></tr>
<tr><td class="k">Hora de inicio</td><td>{{ campo.hora_inicio }}</td>
    <td class="k">Hora de término</td><td>{{ campo.hora_termino }}</td></tr>
</table>

<h2>Diagnósticos</h2>
<p><strong>Preoperatorio:</strong> {{ campo.dx_preoperatorio|parrafos }}</p>
<p><strong>Postoperatorio:</strong> {{ campo.dx_postoperatorio|parrafos }}</p>

<h2>Procedimiento</h2>
<table class="doc-grid">
<tr><td class="k">Cirugía programada</td><td colspan="3">{{ campo.cirugia_programada }}</td></tr>
<tr><td class="k">Cirugía realizada</td><td colspan="3">{{ campo.cirugia_realizada }}</td></tr>
</table>
<p>{{ campo.tecnica|parrafos }}</p>

<h2>Hallazgos</h2>
<p>{{ campo.hallazgos_qx|parrafos }}</p>
<p><strong>Incidentes:</strong> {{ campo.incidentes|parrafos }}</p>
<p><strong>Complicaciones:</strong> {{ campo.complicaciones|parrafos }}</p>

<h2>Cierre</h2>
<table class="doc-grid">
<tr><td class="k">Anatomía patológica</td><td>{{ campo.anatomia_patologica }}</td>
    <td class="k">Número de piezas</td><td>{{ campo.piezas }}</td></tr>
<tr><td class="k">Implantes</td><td>{{ campo.implantes }}</td>
    <td class="k">Destino del paciente</td><td>{{ campo.destino }}</td></tr>
</table>"""
        + """<div class="doc-signatures">
<div class="sign"><div class="line"></div><div class="role">Cirujano principal</div>
<div class="hint">{{ campo.cirujano }}</div></div>
<div class="sign"><div class="line"></div><div class="role">Anestesiólogo</div>
<div class="hint">{{ campo.anestesiologo }}</div></div>
</div>"""
    ),
}

_ALDRETE_ITEMS: tuple[tuple[str, str, list[dict[str, str]]], ...] = (
    ("actividad", "Actividad motora", [
        {"value": "2", "label": "2 — Mueve las cuatro extremidades"},
        {"value": "1", "label": "1 — No mueve dos extremidades"},
        {"value": "0", "label": "0 — No mueve las extremidades"},
    ]),
    ("respiracion", "Respiración", [
        {"value": "2", "label": "2 — Respira y tose normalmente"},
        {"value": "1", "label": "1 — Disnea o respiración limitada"},
        {"value": "0", "label": "0 — Apnea"},
    ]),
    ("circulacion", "Circulación", [
        {"value": "2", "label": "2 — PA hasta 20 % del nivel preanestésico"},
        {"value": "1", "label": "1 — PA entre 20 y 50 % del nivel preanestésico"},
        {"value": "0", "label": "0 — PA más del 50 % del nivel preanestésico"},
    ]),
    ("conciencia", "Conciencia", [
        {"value": "2", "label": "2 — Completamente despierto"},
        {"value": "1", "label": "1 — Despierta al llamado"},
        {"value": "0", "label": "0 — No responde"},
    ]),
    ("saturacion_aldrete", "Saturación", [
        {"value": "2", "label": "2 — SpO₂ mayor de 92 % con aire ambiente"},
        {"value": "1", "label": "1 — Necesita oxígeno para mantener SpO₂ sobre 90 %"},
        {"value": "0", "label": "0 — SpO₂ menor de 90 % con oxígeno suplementario"},
    ]),
)

CUIDADOS_URPA = {
    "code": "FIC-URP",
    "version": 1,
    "family": FICHA,
    "title": "Hoja de cuidados de enfermería en recuperación posanestésica",
    "description": "Escala de Aldrete modificada, dolor, cuidados y alta de la URPA",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "operacion", "label": "Operación realizada", "type": "text", "group": "Ingreso", "required": True, "wide": True},
        {"key": "anestesia_urpa", "label": "Tipo de anestesia", "type": "text", "group": "Ingreso"},
        {"key": "hora_ingreso_urpa", "label": "Hora de ingreso a la URPA", "type": "text", "group": "Ingreso", "placeholder": "10:45"},
        {"key": "cama_urpa", "label": "Cama", "type": "text", "group": "Ingreso"},
        *[
            {"key": key, "label": label, "type": "select", "group": "Escala de Aldrete",
             "options": options, "default": "2", "wide": True}
            for key, label, options in _ALDRETE_ITEMS
        ],
        {
            "key": "aldrete",
            "label": "Puntaje de Aldrete",
            "type": "computed",
            "group": "Escala de Aldrete",
            "sum": [key for key, _, _ in _ALDRETE_ITEMS],
            "help": "Un puntaje de 9 o más permite el alta de la unidad de recuperación.",
        },
        measure("eva_urpa", "Escala visual analógica del dolor (0 a 10)", "Valoración"),
        {"key": "pa_urpa", "label": "Presión arterial (mmHg)", "type": "text", "group": "Valoración", "placeholder": "110/70"},
        measure("fc_urpa", "Frecuencia cardíaca (lpm)", "Valoración"),
        measure("fr_urpa", "Frecuencia respiratoria (rpm)", "Valoración"),
        measure("temperatura_urpa", "Temperatura (°C)", "Valoración"),
        choice("nauseas", "Náuseas o vómitos", "Valoración", SI_NO, "No"),
        choice("sangrado", "Sangrado en la herida operatoria", "Valoración", SI_NO, "No"),
        choice("drenajes", "Drenajes o catéteres", "Valoración", SI_NO, "No"),
        {"key": "terapeutica", "label": "Terapéutica administrada", "type": "textarea", "group": "Cuidados", "wide": True},
        {"key": "cuidados", "label": "Cuidados de enfermería brindados", "type": "textarea", "group": "Cuidados", "required": True, "wide": True},
        {"key": "hora_alta_urpa", "label": "Hora de alta de la URPA", "type": "text", "group": "Alta", "placeholder": "12:30"},
        choice("destino_urpa", "Destino", "Alta",
               opts("Hospitalización", "Alta domiciliaria", "Referido"), "Hospitalización"),
    ],
    "body": (
        HEADER_CLINICAL
        + """<table class="doc-grid">
<tr><td class="k">Operación realizada</td><td colspan="3">{{ campo.operacion }}</td></tr>
<tr><td class="k">Tipo de anestesia</td><td>{{ campo.anestesia_urpa }}</td>
    <td class="k">Cama</td><td>{{ campo.cama_urpa }}</td></tr>
<tr><td class="k">Hora de ingreso</td><td>{{ campo.hora_ingreso_urpa }}</td>
    <td class="k">Hora de alta</td><td>{{ campo.hora_alta_urpa }}</td></tr>
</table>

<h2>Escala de Aldrete modificada</h2>
<table class="doc-table">
<tr><th>Categoría</th><th>Puntaje</th></tr>
<tr><td>Actividad motora</td><td>{{ campo.actividad }}</td></tr>
<tr><td>Respiración</td><td>{{ campo.respiracion }}</td></tr>
<tr><td>Circulación</td><td>{{ campo.circulacion }}</td></tr>
<tr><td>Conciencia</td><td>{{ campo.conciencia }}</td></tr>
<tr><td>Saturación</td><td>{{ campo.saturacion_aldrete }}</td></tr>
<tr><td><strong>Total</strong></td><td><strong>{{ campo.aldrete }} / 10</strong></td></tr>
</table>
<p class="doc-note">Un puntaje de 9 o más permite el alta de la unidad de recuperación
posanestésica.</p>

<h2>Valoración de enfermería</h2>
<table class="doc-table">
<tr><th>PA</th><th>FC</th><th>FR</th><th>T°</th><th>EVA</th></tr>
<tr><td>{{ campo.pa_urpa }}</td><td>{{ campo.fc_urpa }}</td><td>{{ campo.fr_urpa }}</td>
    <td>{{ campo.temperatura_urpa }}</td><td>{{ campo.eva_urpa }} / 10</td></tr>
</table>
<table class="doc-grid">
<tr><td class="k">Náuseas o vómitos</td><td>{{ campo.nauseas }}</td>
    <td class="k">Sangrado</td><td>{{ campo.sangrado }}</td></tr>
<tr><td class="k">Drenajes o catéteres</td><td>{{ campo.drenajes }}</td>
    <td class="k">Destino</td><td>{{ campo.destino_urpa }}</td></tr>
</table>

<h2>Terapéutica y cuidados</h2>
<p>{{ campo.terapeutica|parrafos }}</p>
<p>{{ campo.cuidados|parrafos }}</p>"""
        + """<div class="doc-signatures">
<div class="sign"><div class="line"></div>
<div class="role">Enfermera(o) de la URPA</div>
<div class="hint">{{ profesional.nombre }} · Colegiatura {{ profesional.cmp }}</div></div>
</div>"""
    ),
}



# --- Historia clínica de emergencia ---------------------------------------

HISTORIA_EMERGENCIA = {
    "code": "FIC-EMG",
    "version": 1,
    "family": FICHA,
    "title": "Historia clínica de emergencia",
    "description": "Motivo y relato de la emergencia, examen clínico, diagnóstico y tratamiento",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "hora_ingreso", "label": "Hora de ingreso", "type": "text", "group": "Emergencia", "placeholder": "22:15"},
        {"key": "motivo_emergencia", "label": "Motivo de la emergencia", "type": "text", "group": "Emergencia", "required": True, "wide": True},
        {"key": "relato_emergencia", "label": "Relato de la emergencia", "type": "textarea", "group": "Emergencia", "required": True, "wide": True},
        {"key": "antecedentes_emg", "label": "Antecedentes", "type": "textarea", "group": "Emergencia", "default": "Niega", "wide": True},
        {"key": "pa_emg", "label": "Presión arterial (mmHg)", "type": "text", "group": "Examen clínico", "placeholder": "120/80"},
        measure("fc_emg", "Frecuencia cardíaca (lpm)", "Examen clínico"),
        measure("fr_emg", "Frecuencia respiratoria (rpm)", "Examen clínico"),
        measure("t_emg", "Temperatura (°C)", "Examen clínico"),
        measure("sat_emg", "Saturación de oxígeno (%)", "Examen clínico"),
        measure("peso_emg", "Peso (kg)", "Examen clínico"),
        {"key": "ectoscopia_emg", "label": "Ectoscopía", "type": "text", "group": "Examen clínico", "default": "Aparente regular estado general, lúcido y orientado", "wide": True},
        {"key": "examen_fisico_emg", "label": "Examen físico", "type": "textarea", "group": "Examen clínico", "required": True, "wide": True},
        {"key": "otros_emg", "label": "Otros hallazgos", "type": "textarea", "group": "Examen clínico", "default": "Ninguno", "wide": True},
        {"key": "diagnostico_emg", "label": "Diagnóstico", "type": "textarea", "group": "Diagnóstico y tratamiento", "required": True, "wide": True},
        {"key": "cie10_emg", "label": "CIE-10", "type": "text", "group": "Diagnóstico y tratamiento", "placeholder": "S01.0"},
        {"key": "examenes_emg", "label": "Exámenes auxiliares", "type": "textarea", "group": "Diagnóstico y tratamiento", "default": "Ninguno", "wide": True},
        {"key": "tratamiento_emg", "label": "Tratamiento indicado (Rp.)", "type": "textarea", "group": "Diagnóstico y tratamiento", "required": True, "wide": True},
        # La hoja en papel termina en el Rp. y deja sin registrar en qué acabó
        # la atención, que es lo que después se reclama de un acta de
        # emergencia: si el paciente se fue de alta, quedó en observación o
        # salió referido, y en qué condición.
        choice("destino_emg", "Destino del paciente", "Destino",
               opts("Alta", "Observación", "Hospitalización", "Referencia", "Fallecido"),
               "Alta"),
        choice("condicion_emg", "Condición al egreso", "Destino", ESTADO_PACIENTE, "Estable"),
        {"key": "hora_salida", "label": "Hora de salida", "type": "text", "group": "Destino", "placeholder": "23:40"},
    ],
    "body": (
        HEADER_CLINICAL
        + """<h2>Emergencia</h2>
<table class="doc-grid">
<tr><td class="k">Hora de ingreso</td><td>{{ campo.hora_ingreso }}</td>
    <td class="k">Motivo</td><td>{{ campo.motivo_emergencia }}</td></tr>
</table>
<p><strong>Relato:</strong> {{ campo.relato_emergencia|parrafos }}</p>
<p><strong>Antecedentes:</strong> {{ campo.antecedentes_emg|parrafos }}</p>

<h2>Examen clínico</h2>
<table class="doc-table">
<tr><th>PA</th><th>FC</th><th>FR</th><th>T°</th><th>SatO₂</th><th>Peso</th></tr>
<tr><td>{{ campo.pa_emg }}</td><td>{{ campo.fc_emg }}</td><td>{{ campo.fr_emg }}</td>
    <td>{{ campo.t_emg }}</td><td>{{ campo.sat_emg }} %</td><td>{{ campo.peso_emg }} kg</td></tr>
</table>
<p><strong>Ectoscopía:</strong> {{ campo.ectoscopia_emg }}</p>
<p>{{ campo.examen_fisico_emg|parrafos }}</p>
<p><strong>Otros hallazgos:</strong> {{ campo.otros_emg|parrafos }}</p>

<h2>Diagnóstico</h2>
<p>{{ campo.diagnostico_emg|parrafos }}</p>
<p><strong>CIE-10:</strong> {{ campo.cie10_emg }}</p>

<h2>Exámenes auxiliares</h2>
<p>{{ campo.examenes_emg|parrafos }}</p>

<h2>Tratamiento</h2>
<p>{{ campo.tratamiento_emg|parrafos }}</p>

<h2>Destino</h2>
<table class="doc-grid">
<tr><td class="k">Destino del paciente</td><td>{{ campo.destino_emg }}</td>
    <td class="k">Condición al egreso</td><td>{{ campo.condicion_emg }}</td></tr>
<tr><td class="k">Hora de ingreso</td><td>{{ campo.hora_ingreso }}</td>
    <td class="k">Hora de salida</td><td>{{ campo.hora_salida }}</td></tr>
</table>"""
        + SIGN_DOCTOR
    ),
}


# --- Historia clínica gineco-obstétrica ------------------------------------

# Los antecedentes personales y familiares de la hoja son casillas que se
# marcan; aquí son selectores para que queden consultables entre controles.
_GO_ANTECEDENTES = (
    ("dbm", "Diabetes mellitus"),
    ("hta", "Hipertensión arterial"),
    ("ca", "Cáncer"),
    ("ram", "Reacción adversa a medicamentos"),
    ("qx", "Intervención quirúrgica"),
)

_GO_EXAMEN = (
    ("go_cabeza", "Cabeza y cuello", "Sin alteraciones"),
    ("go_piel", "Piel y mucosas", "Tibias, hidratadas, no palidez"),
    ("go_mamas", "Examen de mamas", "Simétricas, no nódulos, no secreción"),
    ("go_abdomen", "Examen abdominal", "Blando, depresible, no doloroso"),
    ("go_pelvico", "Examen pélvico", "No realizado"),
    ("go_genitourinario", "Examen genitourinario", "Sin alteraciones"),
    ("go_miembros", "Miembros inferiores", "No edemas, no várices"),
)

HISTORIA_GINECO_OBSTETRICA = {
    "code": "FIC-GO",
    "version": 1,
    "family": FICHA,
    "title": "Historia clínica gineco-obstétrica",
    "description": "Antecedentes ginecológicos y obstétricos, examen y diagnóstico",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "go_acompanante", "label": "Acompañante", "type": "text", "group": "Acompañante", "wide": True},
        {"key": "go_parentesco", "label": "Parentesco", "type": "text", "group": "Acompañante"},
        {"key": "go_acomp_telefono", "label": "Teléfono del acompañante", "type": "text", "group": "Acompañante"},
        {"key": "go_pa", "label": "Presión arterial (mmHg)", "type": "text", "group": "Examen clínico", "placeholder": "110/70"},
        measure("go_temp", "Temperatura (°C)", "Examen clínico"),
        measure("go_fc", "Frecuencia cardíaca (lpm)", "Examen clínico"),
        measure("go_fr", "Frecuencia respiratoria (rpm)", "Examen clínico"),
        measure("go_peso", "Peso (kg)", "Examen clínico"),
        measure("go_talla", "Talla (cm)", "Examen clínico"),
        measure("go_imc", "IMC", "Examen clínico"),
        *[
            choice(f"go_ap_{key}", label, "Antecedentes personales", SI_NO, "No")
            for key, label in _GO_ANTECEDENTES
        ],
        {"key": "go_ap_detalle", "label": "Detalle de los antecedentes personales", "type": "text", "group": "Antecedentes personales", "default": "Ninguno", "wide": True},
        {"key": "go_menarquia", "label": "Menarquia (edad)", "type": "text", "group": "Antecedentes ginecológicos", "placeholder": "13 años"},
        {"key": "go_rc", "label": "Régimen catamenial", "type": "text", "group": "Antecedentes ginecológicos", "placeholder": "5/28"},
        {"key": "go_irs", "label": "Inicio de relaciones sexuales (edad)", "type": "text", "group": "Antecedentes ginecológicos"},
        measure("go_parejas", "N.° de parejas sexuales", "Antecedentes ginecológicos"),
        {"key": "go_mac", "label": "Método anticonceptivo", "type": "text", "group": "Antecedentes ginecológicos", "default": "Ninguno"},
        {"key": "go_formula", "label": "Fórmula obstétrica (G / P)", "type": "text", "group": "Antecedentes ginecológicos", "placeholder": "G3 P2-0-1-2"},
        {"key": "go_fp1", "label": "Fecha del parto 1", "type": "text", "group": "Antecedentes ginecológicos"},
        {"key": "go_fp2", "label": "Fecha del parto 2", "type": "text", "group": "Antecedentes ginecológicos"},
        {"key": "go_fp3", "label": "Fecha del parto 3", "type": "text", "group": "Antecedentes ginecológicos"},
        {"key": "go_fp4", "label": "Fecha del parto 4", "type": "text", "group": "Antecedentes ginecológicos"},
        {"key": "go_fur", "label": "FUR · fecha de la última regla", "type": "date", "group": "Antecedentes ginecológicos"},
        {"key": "go_fupap", "label": "FUPAP · último papanicolau", "type": "date", "group": "Antecedentes ginecológicos"},
        {"key": "go_fpp", "label": "FPP · fecha probable de parto", "type": "date", "group": "Antecedentes ginecológicos"},
        {"key": "go_gine_otros", "label": "Otros antecedentes ginecológicos", "type": "text", "group": "Antecedentes ginecológicos", "default": "Ninguno", "wide": True},
        *[
            choice(f"go_af_{key}", label, "Antecedentes familiares", SI_NO, "No")
            for key, label in _GO_ANTECEDENTES
        ],
        {"key": "go_af_detalle", "label": "Detalle de los antecedentes familiares", "type": "text", "group": "Antecedentes familiares", "default": "Ninguno", "wide": True},
        {"key": "go_motivo", "label": "Motivo de la consulta", "type": "text", "group": "Enfermedad actual", "required": True, "wide": True},
        measure("go_tiempo", "Tiempo de enfermedad (días)", "Enfermedad actual"),
        choice("go_inicio", "Forma de inicio", "Enfermedad actual", opts("Insidioso", "Brusco"), "Insidioso"),
        choice("go_curso", "Curso", "Enfermedad actual", opts("Progresivo", "Estacionario", "Remitente"), "Progresivo"),
        {"key": "go_relato", "label": "Relato de la enfermedad", "type": "textarea", "group": "Enfermedad actual", "required": True, "wide": True},
        {"key": "go_ectoscopia", "label": "Ectoscopía", "type": "text", "group": "Examen físico", "default": "Aparente buen estado general, lúcida y orientada", "wide": True},
        *[
            {"key": key, "label": label, "type": "text", "group": "Examen físico", "default": default, "wide": True}
            for key, label, default in _GO_EXAMEN
        ],
        {"key": "go_diagnostico", "label": "Diagnóstico", "type": "textarea", "group": "Diagnóstico y plan", "required": True, "wide": True},
        {"key": "go_cie10", "label": "CIE-10", "type": "text", "group": "Diagnóstico y plan", "placeholder": "Z34.0"},
        {"key": "go_examenes", "label": "Exámenes auxiliares", "type": "textarea", "group": "Diagnóstico y plan", "default": "Ninguno", "wide": True},
        {"key": "go_tratamiento", "label": "Tratamiento", "type": "textarea", "group": "Diagnóstico y plan", "required": True, "wide": True},
        {"key": "go_cita", "label": "Próxima cita", "type": "text", "group": "Diagnóstico y plan"},
    ],
    "body": (
        HEADER_CLINICAL
        + """<table class="doc-grid">
<tr><td class="k">Acompañante</td><td>{{ campo.go_acompanante }}</td>
    <td class="k">Parentesco</td><td>{{ campo.go_parentesco }}</td></tr>
<tr><td class="k">Teléfono</td><td colspan="3">{{ campo.go_acomp_telefono }}</td></tr>
</table>

<h2>Examen clínico</h2>
<table class="doc-table">
<tr><th>PA</th><th>T°</th><th>FC</th><th>FR</th><th>Peso</th><th>Talla</th><th>IMC</th></tr>
<tr><td>{{ campo.go_pa }}</td><td>{{ campo.go_temp }}</td><td>{{ campo.go_fc }}</td>
    <td>{{ campo.go_fr }}</td><td>{{ campo.go_peso }} kg</td><td>{{ campo.go_talla }} cm</td>
    <td>{{ campo.go_imc }}</td></tr>
</table>

<h2>Antecedentes personales</h2>
<table class="doc-table">
<tr><th>DBM</th><th>HTA</th><th>CA</th><th>RAM</th><th>Int. quirúrgica</th></tr>
<tr><td>{{ campo.go_ap_dbm }}</td><td>{{ campo.go_ap_hta }}</td><td>{{ campo.go_ap_ca }}</td>
    <td>{{ campo.go_ap_ram }}</td><td>{{ campo.go_ap_qx }}</td></tr>
</table>
<p>{{ campo.go_ap_detalle }}</p>

<h2>Antecedentes ginecológicos y obstétricos</h2>
<table class="doc-grid">
<tr><td class="k">Menarquia</td><td>{{ campo.go_menarquia }}</td>
    <td class="k">Régimen catamenial</td><td>{{ campo.go_rc }}</td></tr>
<tr><td class="k">Inicio de relaciones</td><td>{{ campo.go_irs }}</td>
    <td class="k">N.° de parejas</td><td>{{ campo.go_parejas }}</td></tr>
<tr><td class="k">Método anticonceptivo</td><td>{{ campo.go_mac }}</td>
    <td class="k">Fórmula obstétrica</td><td>{{ campo.go_formula }}</td></tr>
<tr><td class="k">FUR</td><td>{{ campo.go_fur }}</td>
    <td class="k">FPP</td><td>{{ campo.go_fpp }}</td></tr>
<tr><td class="k">FUPAP</td><td colspan="3">{{ campo.go_fupap }}</td></tr>
</table>
<table class="doc-table">
<tr><th>Parto 1</th><th>Parto 2</th><th>Parto 3</th><th>Parto 4</th></tr>
<tr><td>{{ campo.go_fp1 }}</td><td>{{ campo.go_fp2 }}</td>
    <td>{{ campo.go_fp3 }}</td><td>{{ campo.go_fp4 }}</td></tr>
</table>
<p><strong>Otros:</strong> {{ campo.go_gine_otros }}</p>

<h2>Antecedentes familiares</h2>
<table class="doc-table">
<tr><th>DBM</th><th>HTA</th><th>CA</th><th>RAM</th><th>Int. quirúrgica</th></tr>
<tr><td>{{ campo.go_af_dbm }}</td><td>{{ campo.go_af_hta }}</td><td>{{ campo.go_af_ca }}</td>
    <td>{{ campo.go_af_ram }}</td><td>{{ campo.go_af_qx }}</td></tr>
</table>
<p>{{ campo.go_af_detalle }}</p>

<h2>Enfermedad actual</h2>
<table class="doc-grid">
<tr><td class="k">Motivo de la consulta</td><td colspan="3">{{ campo.go_motivo }}</td></tr>
<tr><td class="k">Tiempo de enfermedad</td><td>{{ campo.go_tiempo }} días</td>
    <td class="k">Inicio y curso</td><td>{{ campo.go_inicio }} · {{ campo.go_curso }}</td></tr>
</table>
<p>{{ campo.go_relato|parrafos }}</p>

<h2>Examen físico</h2>
<p><strong>Ectoscopía:</strong> {{ campo.go_ectoscopia }}</p>
<table class="doc-grid">
<tr><td class="k">Cabeza y cuello</td><td colspan="3">{{ campo.go_cabeza }}</td></tr>
<tr><td class="k">Piel y mucosas</td><td colspan="3">{{ campo.go_piel }}</td></tr>
<tr><td class="k">Mamas</td><td colspan="3">{{ campo.go_mamas }}</td></tr>
<tr><td class="k">Abdomen</td><td colspan="3">{{ campo.go_abdomen }}</td></tr>
<tr><td class="k">Pélvico</td><td colspan="3">{{ campo.go_pelvico }}</td></tr>
<tr><td class="k">Genitourinario</td><td colspan="3">{{ campo.go_genitourinario }}</td></tr>
<tr><td class="k">Miembros inferiores</td><td colspan="3">{{ campo.go_miembros }}</td></tr>
</table>

<h2>Diagnóstico</h2>
<p>{{ campo.go_diagnostico|parrafos }}</p>
<p><strong>CIE-10:</strong> {{ campo.go_cie10 }}</p>

<h2>Exámenes auxiliares</h2>
<p>{{ campo.go_examenes|parrafos }}</p>

<h2>Tratamiento</h2>
<p>{{ campo.go_tratamiento|parrafos }}</p>
<p><strong>Próxima cita:</strong> {{ campo.go_cita }}</p>"""
        + SIGN_DOCTOR
    ),
}

HISTORIA_GINECO_CONTINUADORA = {
    "code": "FIC-GOC",
    "version": 1,
    "family": FICHA,
    "title": "Historia clínica continuadora gineco-obstétrica",
    "description": "Control de seguimiento: examen clínico, evolución, diagnóstico y tratamiento",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "goc_acompanante", "label": "Acompañante", "type": "text", "group": "Acompañante", "wide": True},
        {"key": "goc_parentesco", "label": "Parentesco", "type": "text", "group": "Acompañante"},
        {"key": "goc_acomp_telefono", "label": "Teléfono del acompañante", "type": "text", "group": "Acompañante"},
        {"key": "goc_pa", "label": "Presión arterial (mmHg)", "type": "text", "group": "Examen clínico", "placeholder": "110/70"},
        measure("goc_temp", "Temperatura (°C)", "Examen clínico"),
        measure("goc_fc", "Frecuencia cardíaca (lpm)", "Examen clínico"),
        measure("goc_fr", "Frecuencia respiratoria (rpm)", "Examen clínico"),
        measure("goc_peso", "Peso (kg)", "Examen clínico"),
        measure("goc_talla", "Talla (cm)", "Examen clínico"),
        measure("goc_imc", "IMC", "Examen clínico"),
        {"key": "goc_motivo", "label": "Motivo de la consulta", "type": "textarea", "group": "Control", "required": True, "wide": True},
        {"key": "goc_cabeza", "label": "Cabeza y cuello", "type": "text", "group": "Al examen", "default": "Sin alteraciones", "wide": True},
        {"key": "goc_piel", "label": "Piel y mucosas", "type": "text", "group": "Al examen", "default": "Tibias, hidratadas, no palidez", "wide": True},
        {"key": "goc_mamas", "label": "Examen de mamas", "type": "text", "group": "Al examen", "default": "Simétricas, no nódulos, no secreción", "wide": True},
        {"key": "goc_abdomen", "label": "Examen abdominal", "type": "text", "group": "Al examen", "default": "Blando, depresible, no doloroso", "wide": True},
        {"key": "goc_genitourinario", "label": "Examen genitourinario", "type": "text", "group": "Al examen", "default": "Sin alteraciones", "wide": True},
        {"key": "goc_miembros", "label": "Miembros inferiores", "type": "text", "group": "Al examen", "default": "No edemas, no várices", "wide": True},
        {"key": "goc_diagnostico", "label": "Diagnóstico", "type": "textarea", "group": "Diagnóstico y plan", "required": True, "wide": True},
        {"key": "goc_examenes", "label": "Exámenes auxiliares", "type": "textarea", "group": "Diagnóstico y plan", "default": "Ninguno", "wide": True},
        {"key": "goc_tratamiento", "label": "Tratamiento", "type": "textarea", "group": "Diagnóstico y plan", "required": True, "wide": True},
        {"key": "goc_cita", "label": "Próxima cita", "type": "text", "group": "Diagnóstico y plan"},
    ],
    "body": (
        HEADER_CLINICAL
        + """<table class="doc-grid">
<tr><td class="k">Acompañante</td><td>{{ campo.goc_acompanante }}</td>
    <td class="k">Parentesco</td><td>{{ campo.goc_parentesco }}</td></tr>
<tr><td class="k">Teléfono</td><td colspan="3">{{ campo.goc_acomp_telefono }}</td></tr>
</table>

<h2>Examen clínico</h2>
<table class="doc-table">
<tr><th>PA</th><th>T°</th><th>FC</th><th>FR</th><th>Peso</th><th>Talla</th><th>IMC</th></tr>
<tr><td>{{ campo.goc_pa }}</td><td>{{ campo.goc_temp }}</td><td>{{ campo.goc_fc }}</td>
    <td>{{ campo.goc_fr }}</td><td>{{ campo.goc_peso }} kg</td><td>{{ campo.goc_talla }} cm</td>
    <td>{{ campo.goc_imc }}</td></tr>
</table>

<h2>Motivo de la consulta</h2>
<p>{{ campo.goc_motivo|parrafos }}</p>

<h2>Al examen</h2>
<table class="doc-grid">
<tr><td class="k">Cabeza y cuello</td><td colspan="3">{{ campo.goc_cabeza }}</td></tr>
<tr><td class="k">Piel y mucosas</td><td colspan="3">{{ campo.goc_piel }}</td></tr>
<tr><td class="k">Mamas</td><td colspan="3">{{ campo.goc_mamas }}</td></tr>
<tr><td class="k">Abdomen</td><td colspan="3">{{ campo.goc_abdomen }}</td></tr>
<tr><td class="k">Genitourinario</td><td colspan="3">{{ campo.goc_genitourinario }}</td></tr>
<tr><td class="k">Miembros inferiores</td><td colspan="3">{{ campo.goc_miembros }}</td></tr>
</table>

<h2>Diagnóstico</h2>
<p>{{ campo.goc_diagnostico|parrafos }}</p>

<h2>Exámenes auxiliares</h2>
<p>{{ campo.goc_examenes|parrafos }}</p>

<h2>Tratamiento</h2>
<p>{{ campo.goc_tratamiento|parrafos }}</p>
<p><strong>Próxima cita:</strong> {{ campo.goc_cita }}</p>"""
        + SIGN_DOCTOR
    ),
}


# --- Historia clínica odontológica -----------------------------------------

HISTORIA_ODONTOLOGICA = {
    "code": "FIC-ODO",
    "version": 1,
    "family": FICHA,
    "title": "Historia clínica odontológica",
    "description": "Anamnesis, examen odontoestomatológico, diagnóstico, pronóstico y plan",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "odo_procedencia", "label": "Procedencia", "type": "text", "group": "Filiación"},
        {"key": "odo_motivo", "label": "Motivo de la consulta", "type": "text", "group": "Anamnesis", "required": True, "wide": True},
        {"key": "odo_enfermedad", "label": "Enfermedad actual", "type": "textarea", "group": "Anamnesis", "required": True, "wide": True},
        measure("odo_tiempo", "Tiempo de enfermedad (días)", "Anamnesis"),
        {"key": "odo_signos", "label": "Signos y síntomas principales", "type": "text", "group": "Anamnesis", "wide": True},
        {"key": "odo_relato", "label": "Relato cronológico", "type": "textarea", "group": "Anamnesis", "wide": True},
        {"key": "odo_funciones", "label": "Funciones biológicas", "type": "text", "group": "Anamnesis", "default": "Conservadas", "wide": True},
        {"key": "odo_ant_familiares", "label": "Antecedentes familiares", "type": "textarea", "group": "Antecedentes", "default": "Niega", "wide": True},
        {"key": "odo_ant_personales", "label": "Antecedentes personales", "type": "textarea", "group": "Antecedentes", "default": "Niega", "wide": True},
        {"key": "odo_pa", "label": "Presión arterial (mmHg)", "type": "text", "group": "Signos vitales", "placeholder": "120/80"},
        measure("odo_pulso", "Pulso (lpm)", "Signos vitales"),
        measure("odo_temp", "Temperatura (°C)", "Signos vitales"),
        measure("odo_fc", "Frecuencia cardíaca (lpm)", "Signos vitales"),
        measure("odo_fr", "Frecuencia respiratoria (rpm)", "Signos vitales"),
        {"key": "odo_examen_general", "label": "Examen clínico general", "type": "textarea", "group": "Examen clínico", "default": "Sin alteraciones", "wide": True},
        {"key": "odo_examen_esto", "label": "Examen clínico odontoestomatológico", "type": "textarea", "group": "Examen clínico", "required": True, "wide": True},
        {"key": "odo_odontograma", "label": "Odontograma", "type": "odontograma", "group": "Odontograma",
         "help": "Notación FDI. Se marca la cara de la pieza, o el número para la pieza entera."},
        {"key": "odo_odontograma_notas", "label": "Observaciones del odontograma", "type": "textarea", "group": "Odontograma", "default": "Ninguna", "wide": True},
        {"key": "odo_dx_presuntivo", "label": "Diagnóstico presuntivo", "type": "textarea", "group": "Diagnóstico", "required": True, "wide": True},
        {"key": "odo_dx_definitivo", "label": "Diagnóstico definitivo", "type": "textarea", "group": "Diagnóstico", "wide": True},
        {"key": "odo_plan", "label": "Plan de tratamiento", "type": "textarea", "group": "Plan", "required": True, "wide": True},
        choice("odo_pronostico", "Pronóstico", "Plan",
               opts("Favorable", "Reservado", "Desfavorable"), "Favorable"),
        {"key": "odo_tratamiento", "label": "Tratamiento y recomendaciones", "type": "textarea", "group": "Plan", "required": True, "wide": True},
        {"key": "odo_control", "label": "Control y evolución", "type": "textarea", "group": "Plan", "default": "Pendiente", "wide": True},
    ],
    "body": (
        HEADER_CLINICAL
        + """<h2>Filiación</h2>
<table class="doc-grid">
<tr><td class="k">Procedencia</td><td>{{ campo.odo_procedencia }}</td>
    <td class="k">Ocupación</td><td>{{ paciente.ocupacion }}</td></tr>
<tr><td class="k">Domicilio</td><td colspan="3">{{ paciente.direccion }}</td></tr>
</table>

<h2>Anamnesis</h2>
<table class="doc-grid">
<tr><td class="k">Motivo de la consulta</td><td colspan="3">{{ campo.odo_motivo }}</td></tr>
<tr><td class="k">Tiempo de enfermedad</td><td>{{ campo.odo_tiempo }} días</td>
    <td class="k">Funciones biológicas</td><td>{{ campo.odo_funciones }}</td></tr>
</table>
<p><strong>Enfermedad actual:</strong> {{ campo.odo_enfermedad|parrafos }}</p>
<p><strong>Signos y síntomas principales:</strong> {{ campo.odo_signos }}</p>
<p><strong>Relato cronológico:</strong> {{ campo.odo_relato|parrafos }}</p>

<h2>Antecedentes</h2>
<table class="doc-grid">
<tr><td class="k">Familiares</td><td colspan="3">{{ campo.odo_ant_familiares }}</td></tr>
<tr><td class="k">Personales</td><td colspan="3">{{ campo.odo_ant_personales }}</td></tr>
</table>

<h2>Signos vitales</h2>
<table class="doc-table">
<tr><th>PA</th><th>Pulso</th><th>T°</th><th>FC</th><th>FR</th></tr>
<tr><td>{{ campo.odo_pa }}</td><td>{{ campo.odo_pulso }}</td><td>{{ campo.odo_temp }}</td>
    <td>{{ campo.odo_fc }}</td><td>{{ campo.odo_fr }}</td></tr>
</table>

<h2>Examen clínico</h2>
<p><strong>General:</strong> {{ campo.odo_examen_general|parrafos }}</p>
<p><strong>Odontoestomatológico:</strong> {{ campo.odo_examen_esto|parrafos }}</p>

<h2>Odontograma</h2>
{{ campo.odo_odontograma|odontograma }}
<p><strong>Observaciones:</strong> {{ campo.odo_odontograma_notas|parrafos }}</p>

<h2>Diagnóstico</h2>
<p><strong>Presuntivo:</strong> {{ campo.odo_dx_presuntivo|parrafos }}</p>
<p><strong>Definitivo:</strong> {{ campo.odo_dx_definitivo|parrafos }}</p>

<h2>Plan de tratamiento</h2>
<p>{{ campo.odo_plan|parrafos }}</p>
<p><strong>Pronóstico:</strong> {{ campo.odo_pronostico }}</p>

<h2>Tratamiento y recomendaciones</h2>
<p>{{ campo.odo_tratamiento|parrafos }}</p>

<h2>Control y evolución</h2>
<p>{{ campo.odo_control|parrafos }}</p>"""
        + """<div class="doc-signatures">
<div class="sign"><div class="line"></div>
<div class="role">Cirujano dentista</div>
<div class="hint">{{ profesional.nombre }} · COP {{ profesional.cmp }}</div></div>
</div>"""
    ),
}


# --- Procedimientos estéticos ----------------------------------------------

# Las dos hojas comparten las mismas nueve áreas faciales y la misma cabecera;
# solo cambian el producto y la unidad en que se anota lo aplicado.
_AREAS_FACIALES = (
    ("frontal", "Frontal"),
    ("corrugador", "Corrugador"),
    ("orbicular", "Orbicular de los ojos"),
    ("nasal", "Nasal"),
    ("elevador", "Elevador del labio superior"),
    ("masetero", "Masetero"),
    ("depresor", "Depresor del ángulo de la boca"),
    ("mentalis", "Borla del mentón / mentalis"),
    ("platisma", "Platisma del cuello"),
)


def _ficha_estetica(code: str, title: str, description: str, unidad: str, rol: str) -> dict[str, Any]:
    """Hoja de un procedimiento estético aplicado por áreas faciales."""
    filas = "".join(
        f"<tr><td>{label}</td><td>{{{{ campo.area_{key} }}}}</td></tr>"
        for key, label in _AREAS_FACIALES
    )
    return {
        "code": code,
        "version": 1,
        "family": FICHA,
        "title": title,
        "description": description,
        "study_type": None,
        "requires_signature": True,
        "fields": [
            choice("est_previo", "Tratamiento previo", "Antecedente del tratamiento", SI_NO, "No"),
            {"key": "est_producto", "label": "Producto aplicado", "type": "text", "group": "Antecedente del tratamiento", "wide": True},
            {"key": "est_ultima", "label": "Fecha de la última aplicación", "type": "date", "group": "Antecedente del tratamiento"},
            {"key": "est_regiones", "label": "Regiones de aplicación", "type": "text", "group": "Antecedente del tratamiento", "wide": True},
            *[
                measure(f"area_{key}", f"{label} ({unidad})", "Áreas tratadas")
                for key, label in _AREAS_FACIALES
            ],
            {"key": "est_fecha", "label": "Fecha de aplicación", "type": "date", "group": "Aplicación", "required": True},
            {"key": "est_observaciones", "label": "Observaciones del médico", "type": "textarea", "group": "Aplicación", "default": "Ninguna", "wide": True},
            {"key": "est_control", "label": "Próxima cita de control", "type": "date", "group": "Aplicación"},
        ],
        "body": (
            HEADER_CLINICAL
            + f"""<h2>Antecedente del tratamiento</h2>
<table class="doc-grid">
<tr><td class="k">Tratamiento previo</td><td>{{{{ campo.est_previo }}}}</td>
    <td class="k">Producto aplicado</td><td>{{{{ campo.est_producto }}}}</td></tr>
<tr><td class="k">Última aplicación</td><td>{{{{ campo.est_ultima }}}}</td>
    <td class="k">Regiones</td><td>{{{{ campo.est_regiones }}}}</td></tr>
</table>

<h2>Áreas tratadas</h2>
<table class="doc-table">
<tr><th>Área</th><th>{unidad.capitalize()}</th></tr>
{filas}</table>

<h2>Aplicación</h2>
<table class="doc-grid">
<tr><td class="k">Fecha de aplicación</td><td>{{{{ campo.est_fecha }}}}</td>
    <td class="k">Próximo control</td><td>{{{{ campo.est_control }}}}</td></tr>
</table>
<p><strong>Observaciones:</strong> {{{{ campo.est_observaciones|parrafos }}}}</p>"""
            + f"""<div class="doc-signatures">
<div class="sign"><div class="line"></div>
<div class="role">Firma del paciente</div>
<div class="hint">{{{{ paciente.nombre_completo }}}} · {{{{ paciente.tipo_documento }}}} {{{{ paciente.documento }}}}</div></div>
<div class="sign"><div class="line"></div>
<div class="role">{rol}</div>
<div class="hint">{{{{ profesional.nombre }}}} · CMP {{{{ profesional.cmp }}}}</div></div>
</div>"""
        ),
    }


HISTORIA_BOTOX = _ficha_estetica(
    "FIC-BTX",
    "Historia clínica de toxina botulínica",
    "Áreas faciales tratadas y unidades aplicadas",
    "unidades",
    "Médico que aplica",
)

HISTORIA_PLASMA = _ficha_estetica(
    "FIC-PRP",
    "Historia clínica de plasma rico en plaquetas",
    "Áreas faciales tratadas y volumen aplicado",
    "unidades",
    "Médico que aplica",
)


# --- Atención integral del niño --------------------------------------------

# Signos de peligro del formato MINSA, agrupados por edad como en la hoja.
_PELIGRO_MENOR_2M = (
    ("pel_mama", "No quiere mamar ni succiona"),
    ("pel_convul_rn", "Convulsiones"),
    ("pel_fontanela", "Fontanela abombada"),
    ("pel_ombligo", "Enrojecimiento del ombligo que se extiende a la piel"),
    ("pel_fiebre", "Fiebre o temperatura baja"),
    ("pel_nuca", "Rigidez de nuca"),
    ("pel_pustulas", "Pústulas muchas y extensas"),
    ("pel_letargico_rn", "Letárgico o comatoso"),
)

_PELIGRO_2M_4A = (
    ("pel_beber", "No puede beber ni tomar pecho"),
    ("pel_convul", "Convulsiones"),
    ("pel_letargico", "Letárgico o comatoso"),
    ("pel_vomita", "Vomita todo"),
    ("pel_estridor", "Estridor en reposo o tiraje subcostal"),
)

_PELIGRO_TODAS = (
    ("pel_emaciacion", "Emaciación visible grave"),
    ("pel_piel", "La piel vuelve muy lentamente"),
    ("pel_trauma", "Traumatismos o quemaduras"),
    ("pel_envenenamiento", "Envenenamiento"),
    ("pel_palidez", "Palidez palmar intensa"),
)

_PELIGRO_TODOS = _PELIGRO_MENOR_2M + _PELIGRO_2M_4A + _PELIGRO_TODAS


def _peligro_filas(items: tuple[tuple[str, str], ...]) -> str:
    return "".join(
        f"<tr><td>{label}</td><td>{{{{ campo.{key} }}}}</td></tr>" for key, label in items
    )


ATENCION_INTEGRAL_NINO = {
    "code": "FIC-CRED",
    "version": 1,
    "family": FICHA,
    "title": "Atención integral de la niña y el niño",
    "description": "Signos de peligro, anamnesis, crecimiento, desarrollo psicomotor y acuerdos",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        *[
            choice(key, label, "Signos de peligro · menor de 2 meses", AUSENTE_PRESENTE, "Ausente")
            for key, label in _PELIGRO_MENOR_2M
        ],
        *[
            choice(key, label, "Signos de peligro · de 2 meses a 4 años", AUSENTE_PRESENTE, "Ausente")
            for key, label in _PELIGRO_2M_4A
        ],
        *[
            choice(key, label, "Signos de peligro · todas las edades", AUSENTE_PRESENTE, "Ausente")
            for key, label in _PELIGRO_TODAS
        ],
        {"key": "cred_cuidador", "label": "¿Quién cuida al niño o niña?", "type": "text", "group": "Factores de riesgo", "required": True, "wide": True},
        choice("cred_padre", "¿Participa el padre en el cuidado?", "Factores de riesgo", SI_NO, "Sí"),
        choice("cred_afecto", "¿Recibe muestras de afecto?", "Factores de riesgo", SI_NO, "Sí"),
        {"key": "cred_riesgo_detalle", "label": "Especifique los factores de riesgo", "type": "textarea", "group": "Factores de riesgo", "default": "Ninguno", "wide": True},
        {"key": "cred_motivo", "label": "Motivo de consulta", "type": "text", "group": "Anamnesis", "required": True, "wide": True},
        measure("cred_tiempo", "Tiempo de enfermedad (días)", "Anamnesis"),
        choice("cred_inicio", "Forma de inicio", "Anamnesis", opts("Insidioso", "Brusco"), "Insidioso"),
        choice("cred_curso", "Curso", "Anamnesis", opts("Progresivo", "Estacionario", "Remitente"), "Progresivo"),
        measure("cred_temp", "Temperatura (°C)", "Examen físico"),
        {"key": "cred_pa", "label": "Presión arterial (mmHg)", "type": "text", "group": "Examen físico"},
        measure("cred_fc", "Frecuencia cardíaca (lpm)", "Examen físico"),
        measure("cred_fr", "Frecuencia respiratoria (rpm)", "Examen físico"),
        measure("cred_peso", "Peso (kg)", "Examen físico"),
        measure("cred_talla", "Talla (cm)", "Examen físico"),
        measure("cred_pc", "Perímetro cefálico (cm)", "Examen físico"),
        {"key": "cred_examen", "label": "Hallazgos del examen físico", "type": "textarea", "group": "Examen físico", "default": "Sin alteraciones", "wide": True},
        {"key": "cred_dx_nosologico", "label": "Diagnóstico nosológico o sindrómico", "type": "textarea", "group": "Diagnóstico", "required": True, "wide": True},
        choice("cred_crecimiento", "Condición del crecimiento", "Diagnóstico",
               opts("Crecimiento adecuado", "Crecimiento inadecuado"), "Crecimiento adecuado"),
        choice("cred_nutricional", "Estado nutricional", "Diagnóstico",
               opts("Normal", "Ganancia inadecuada de peso o talla", "Desnutrición",
                    "Sobrepeso", "Obesidad"), "Normal"),
        {"key": "cred_pe", "label": "P/E", "type": "text", "group": "Diagnóstico", "placeholder": "Normal"},
        {"key": "cred_te", "label": "T/E", "type": "text", "group": "Diagnóstico", "placeholder": "Normal"},
        {"key": "cred_pt", "label": "P/T", "type": "text", "group": "Diagnóstico", "placeholder": "Normal"},
        choice("cred_desarrollo", "Condición del desarrollo psicomotor", "Diagnóstico",
               opts("Normal", "Riesgo para el desarrollo", "Déficit del desarrollo",
                    "Trastorno del desarrollo"), "Normal"),
        {"key": "cred_desarrollo_obs", "label": "Observaciones del desarrollo", "type": "text", "group": "Diagnóstico", "default": "Ninguna", "wide": True},
        {"key": "cred_factores", "label": "Factores condicionales de la salud, nutrición y desarrollo", "type": "textarea", "group": "Diagnóstico", "default": "Ninguno", "wide": True},
        {"key": "cred_tratamiento", "label": "Tratamiento", "type": "textarea", "group": "Plan", "required": True, "wide": True},
        {"key": "cred_acuerdos", "label": "Acuerdos y compromisos con la madre o cuidador", "type": "textarea", "group": "Plan", "required": True, "wide": True},
        {"key": "cred_examenes", "label": "Exámenes auxiliares", "type": "textarea", "group": "Plan", "default": "Ninguno", "wide": True},
        {"key": "cred_referencia", "label": "Referencia (lugar y motivo)", "type": "text", "group": "Plan", "default": "No amerita", "wide": True},
        {"key": "cred_cita", "label": "Próxima cita", "type": "text", "group": "Plan"},
    ],
    "body": (
        HEADER_CLINICAL
        + """<h2>Descarte de signos de peligro</h2>
<table class="doc-table">
<tr><th>Menor de 2 meses</th><th></th></tr>"""
        + _peligro_filas(_PELIGRO_MENOR_2M)
        + """</table>
<table class="doc-table">
<tr><th>De 2 meses a 4 años</th><th></th></tr>"""
        + _peligro_filas(_PELIGRO_2M_4A)
        + """</table>
<table class="doc-table">
<tr><th>Para todas las edades</th><th></th></tr>"""
        + _peligro_filas(_PELIGRO_TODAS)
        + """</table>

<h2>Factores de riesgo</h2>
<table class="doc-grid">
<tr><td class="k">¿Quién cuida al niño o niña?</td><td colspan="3">{{ campo.cred_cuidador }}</td></tr>
<tr><td class="k">Participa el padre</td><td>{{ campo.cred_padre }}</td>
    <td class="k">Recibe muestras de afecto</td><td>{{ campo.cred_afecto }}</td></tr>
</table>
<p>{{ campo.cred_riesgo_detalle|parrafos }}</p>

<h2>Anamnesis</h2>
<table class="doc-grid">
<tr><td class="k">Motivo de consulta</td><td colspan="3">{{ campo.cred_motivo }}</td></tr>
<tr><td class="k">Tiempo de enfermedad</td><td>{{ campo.cred_tiempo }} días</td>
    <td class="k">Inicio y curso</td><td>{{ campo.cred_inicio }} · {{ campo.cred_curso }}</td></tr>
</table>

<h2>Examen físico</h2>
<table class="doc-table">
<tr><th>T°</th><th>PA</th><th>FC</th><th>FR</th><th>Peso</th><th>Talla</th><th>PC</th></tr>
<tr><td>{{ campo.cred_temp }}</td><td>{{ campo.cred_pa }}</td><td>{{ campo.cred_fc }}</td>
    <td>{{ campo.cred_fr }}</td><td>{{ campo.cred_peso }} kg</td><td>{{ campo.cred_talla }} cm</td>
    <td>{{ campo.cred_pc }} cm</td></tr>
</table>
<p>{{ campo.cred_examen|parrafos }}</p>

<h2>Diagnóstico</h2>
<p><strong>1. Nosológico o sindrómico:</strong> {{ campo.cred_dx_nosologico|parrafos }}</p>
<table class="doc-grid">
<tr><td class="k">2. Crecimiento</td><td>{{ campo.cred_crecimiento }}</td>
    <td class="k">Estado nutricional</td><td>{{ campo.cred_nutricional }}</td></tr>
<tr><td class="k">P/E</td><td>{{ campo.cred_pe }}</td>
    <td class="k">T/E</td><td>{{ campo.cred_te }}</td></tr>
<tr><td class="k">P/T</td><td colspan="3">{{ campo.cred_pt }}</td></tr>
<tr><td class="k">3. Desarrollo psicomotor</td><td colspan="3">{{ campo.cred_desarrollo }}</td></tr>
<tr><td class="k">Observaciones</td><td colspan="3">{{ campo.cred_desarrollo_obs }}</td></tr>
</table>
<p><strong>4. Factores condicionales:</strong> {{ campo.cred_factores|parrafos }}</p>

<h2>Tratamiento</h2>
<p>{{ campo.cred_tratamiento|parrafos }}</p>

<h2>Acuerdos y compromisos</h2>
<p>{{ campo.cred_acuerdos|parrafos }}</p>

<table class="doc-grid">
<tr><td class="k">Exámenes auxiliares</td><td colspan="3">{{ campo.cred_examenes }}</td></tr>
<tr><td class="k">Referencia</td><td>{{ campo.cred_referencia }}</td>
    <td class="k">Próxima cita</td><td>{{ campo.cred_cita }}</td></tr>
</table>"""
        + SIGN_DOCTOR
    ),
}


# --- Tamizaje de violencia y maltrato infantil ------------------------------

# La hoja del MINSA lista los indicadores para que el profesional los marque
# sobre el papel. Aquí se imprimen como referencia y se registra, por
# categoría, si hay indicios y cuáles: el hallazgo es narrativo y anotarlo en
# treinta y cuatro casillas sueltas haría la ficha impracticable.
_VMI_CATEGORIAS = (
    ("fisico", "Físicos", (
        "Hematomas o contusiones inexplicables",
        "Cicatrices y quemaduras",
        "Fracturas inexplicables",
        "Marcas de mordedura",
        "Lesiones de perineo, vulva o recto",
        "Laceraciones en boca, mejillas u ojos",
        "Quejas crónicas sin causa física (cefalea, problemas de sueño)",
        "Problemas con el apetito",
        "Enuresis",
    )),
    ("conductual", "Conductuales", (
        "Retraimiento",
        "Llanto fuerte",
        "Exagerada necesidad de ganar o sobresalir",
        "Demanda excesiva de atención",
        "Mucha agresividad o mucha pasividad frente a otros niños",
        "Tartamudeo",
        "Temor a los padres o de llegar al hogar",
        "Robo, mentira, fuga, desobediencia, agresividad",
        "Ausentismo escolar",
        "Llegar temprano a la escuela o retirarse tarde",
        "Bajo rendimiento académico",
    )),
    ("sexual", "Sexuales", (
        "Conocimiento y conducta sexual inapropiados para la edad",
        "Irritación, dolor, lesión o hemorragia en zona genital",
        "Enfermedad de transmisión sexual",
    )),
    ("negligencia", "Negligencia", (
        "Falta de peso o pobre patrón de crecimiento",
        "Sin vacunas o sin atención de salud",
        "Accidentes o enfermedades muy frecuentes",
        "Descuido en higiene o aliño",
        "Falta de estimulación del desarrollo",
        "Fatiga, sueño o hambre",
    )),
    ("psicologico", "Psicológicos", (
        "Extrema falta de confianza en sí mismo",
        "Aislamiento de personas",
        "Tristeza, depresión o angustia",
        "Intento de suicidio",
    )),
)

_VMI_REFERENCIA = "".join(
    f"<tr><td class=\"k\">{titulo}</td><td>{'; '.join(indicadores)}</td></tr>"
    for _, titulo, indicadores in _VMI_CATEGORIAS
)

TAMIZAJE_VIOLENCIA_INFANTIL = {
    "code": "FIC-VMI",
    "version": 1,
    "family": FICHA,
    "title": "Tamizaje de violencia y maltrato infantil",
    "description": "Preguntas al cuidador e indicadores de maltrato observados en el niño o niña",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        choice("vmi_adulto", "¿Algún miembro de su familia lo insulta, golpea, chantajea u obliga a tener relaciones sexuales?",
               "Preguntas al adulto", SI_NO, "No"),
        {"key": "vmi_quien", "label": "¿Quién?", "type": "text", "group": "Preguntas al adulto", "wide": True},
        choice("vmi_desobediente", "¿Su hijo o hija es muy desobediente?",
               "Preguntas al cuidador", SI_NO, "No"),
        choice("vmi_control", "¿Alguna vez pierde el control y lo golpea?",
               "Preguntas al cuidador", SI_NO, "No"),
        *[
            campo
            for key, titulo, _ in _VMI_CATEGORIAS
            for campo in (
                choice(f"vmi_{key}", f"Indicadores {titulo.lower()}", "Indicadores observados",
                       AUSENTE_PRESENTE, "Ausente"),
                {"key": f"vmi_{key}_detalle", "label": f"¿Cuáles? · {titulo.lower()}",
                 "type": "text", "group": "Indicadores observados", "wide": True},
            )
        ],
        choice("vmi_resultado", "Resultado del tamizaje", "Conclusión",
               opts("Negativo", "Positivo"), "Negativo"),
        {"key": "vmi_conducta", "label": "Conducta adoptada y derivación", "type": "textarea", "group": "Conclusión", "required": True, "wide": True},
    ],
    "body": (
        HEADER_CLINICAL
        + """<p>Debido a que la violencia familiar es dañina para la salud de las personas, se
pregunta en todas las oportunidades de contacto si existe esa situación, para participar
con la familia en la solución de sus problemas.</p>

<h2>Preguntas al adulto</h2>
<table class="doc-grid">
<tr><td class="k">¿Algún miembro de su familia lo insulta, golpea, chantajea u obliga a
    tener relaciones sexuales?</td><td>{{ campo.vmi_adulto }}</td></tr>
<tr><td class="k">¿Quién?</td><td>{{ campo.vmi_quien }}</td></tr>
<tr><td class="k">¿Su hijo o hija es muy desobediente?</td><td>{{ campo.vmi_desobediente }}</td></tr>
<tr><td class="k">¿Alguna vez pierde el control y lo golpea?</td><td>{{ campo.vmi_control }}</td></tr>
</table>

<h2>Indicadores observados</h2>
<table class="doc-table">
<tr><th>Categoría</th><th>Indicios</th><th>¿Cuáles?</th></tr>
<tr><td>Físicos</td><td>{{ campo.vmi_fisico }}</td><td>{{ campo.vmi_fisico_detalle }}</td></tr>
<tr><td>Conductuales</td><td>{{ campo.vmi_conductual }}</td><td>{{ campo.vmi_conductual_detalle }}</td></tr>
<tr><td>Sexuales</td><td>{{ campo.vmi_sexual }}</td><td>{{ campo.vmi_sexual_detalle }}</td></tr>
<tr><td>Negligencia</td><td>{{ campo.vmi_negligencia }}</td><td>{{ campo.vmi_negligencia_detalle }}</td></tr>
<tr><td>Psicológicos</td><td>{{ campo.vmi_psicologico }}</td><td>{{ campo.vmi_psicologico_detalle }}</td></tr>
</table>

<h2>Conclusión</h2>
<table class="doc-grid">
<tr><td class="k">Resultado del tamizaje</td><td>{{ campo.vmi_resultado }}</td></tr>
</table>
<p>{{ campo.vmi_conducta|parrafos }}</p>

<h2>Indicadores de referencia</h2>
<table class="doc-grid">"""
        + _VMI_REFERENCIA
        + """</table>
<p class="doc-note">Adaptado de las Normas y Procedimientos para la Atención de la
Violencia Familiar y el Maltrato Infantil, MINSA.</p>"""
        + SIGN_DOCTOR
    ),
}


# --- Familia C · Consentimientos y declaraciones ---------------------------

CI_PROCEDIMIENTOS = {
    "code": "CI-PROC",
    "version": 1,
    "family": CONSENTIMIENTO,
    "title": "Consentimiento informado para procedimientos",
    "description": "Consentimiento general previo a un procedimiento",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "procedimiento", "label": "Procedimiento a realizar", "type": "textarea", "group": "Procedimiento", "required": True, "wide": True},
        {"key": "riesgos", "label": "Riesgos informados", "type": "textarea", "group": "Procedimiento", "wide": True},
    ],
    "body": (
        PLACE_AND_DATE
        + """<p>Yo, <strong>{{ paciente.nombre_completo }}</strong>, identificado(a) con
{{ paciente.tipo_documento }} N.° {{ paciente.documento }}, historia clínica N.°
{{ paciente.historia }}, habiendo recibido consejería e información acerca del
procedimiento que se me va a realizar, que consta en:</p>

<p style="padding-left:16px"><em>{{ campo.procedimiento|parrafos }}</em></p>

<p>y siendo consciente de los riesgos personalizados, reales y potenciales de la
intervención a la que voy a someterme, que me han sido explicados en lenguaje claro
y sencillo por el(la) profesional <strong>{{ profesional.nombre }}</strong>
(CMP {{ profesional.cmp }}), firmo este consentimiento en pleno uso de mis facultades
físicas y mentales.</p>

<p><strong>Riesgos informados:</strong> {{ campo.riesgos|parrafos }}</p>

<p>Declaro que he tenido la oportunidad de formular las preguntas que consideré
oportunas y que han sido absueltas de manera satisfactoria. Conozco que la actividad
médica no puede garantizar resultados, dados los múltiples factores que inciden en la
recuperación del estado de salud.</p>"""
        + SIGN_PATIENT_DOCTOR
    ),
}

CI_VIH = {
    "code": "CI-VIH",
    "version": 1,
    "family": CONSENTIMIENTO,
    "title": "Consentimiento informado para la prueba de despistaje del VIH",
    "description": "Consejería previa y autorización de la prueba",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        choice("decision", "Decisión del usuario", "Decisión", opts("Acepto", "No acepto"), "Acepto"),
        {"key": "consejero", "label": "Consejero(a) que informó", "type": "text", "group": "Decisión", "wide": True},
    ],
    "body": (
        PLACE_AND_DATE
        + """<p>Yo, <strong>{{ paciente.nombre_completo }}</strong>, identificado(a) con
{{ paciente.tipo_documento }} N.° {{ paciente.documento }}, declaro que he recibido
consejería previa por parte de {{ campo.consejero }}, en la que se me ha informado
sobre:</p>

<ol>
<li>El significado de la prueba de despistaje del VIH y el procedimiento para tomar
    la muestra.</li>
<li>El carácter voluntario de la prueba y mi derecho a rehusarme sin que ello afecte
    la atención que reciba.</li>
<li>La confidencialidad del resultado, que solo será entregado a mi persona o a quien
    yo designe expresamente.</li>
<li>El significado de un resultado reactivo y no reactivo, y la necesidad de una prueba
    confirmatoria en el primer caso.</li>
<li>La existencia del período de ventana y la conveniencia de repetir la prueba.</li>
</ol>

<p>En pleno uso de mis facultades mentales y de manera libre y voluntaria,
<strong>{{ campo.decision|mayus }}</strong> que se me realice la prueba de despistaje
del VIH en {{ clinica.nombre }}.</p>"""
        + SIGN_PATIENT_DOCTOR
    ),
}

CI_HOSPITALIZACION = {
    "code": "CI-HOSP",
    "version": 1,
    "family": CONSENTIMIENTO,
    "title": "Consentimiento informado para hospitalización",
    "description": "Autorización de internamiento y de los procedimientos asociados",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "diagnostico_1", "label": "Diagnóstico presuntivo 1", "type": "text", "group": "Diagnósticos", "required": True, "wide": True},
        {"key": "diagnostico_2", "label": "Diagnóstico presuntivo 2", "type": "text", "group": "Diagnósticos", "wide": True},
        {"key": "designado", "label": "Persona designada para recibir información", "type": "text", "group": "Confidencialidad", "required": True, "wide": True},
        {"key": "parentesco", "label": "Parentesco", "type": "text", "group": "Confidencialidad"},
    ],
    "body": (
        PLACE_AND_DATE
        + """<p>El(la) profesional <strong>{{ profesional.nombre }}</strong>
(CMP {{ profesional.cmp }}) me ha explicado que es conveniente que se me hospitalice
por presentar los siguientes diagnósticos presuntivos:</p>

<ol>
<li>{{ campo.diagnostico_1 }}</li>
<li>{{ campo.diagnostico_2 }}</li>
</ol>

<p>Asimismo, se me informó en forma clara y precisa sobre los riesgos y complicaciones
que conlleva todo acto médico, y también sobre los beneficios esperados de aceptar la
hospitalización. Por ello, declarando que he sido satisfactoriamente informado(a),
<strong>ACEPTO</strong> la hospitalización y <strong>AUTORIZO</strong> al personal de
{{ clinica.nombre }} para que efectúe los procedimientos médicos de diagnóstico y
terapéuticos necesarios de acuerdo con mis condiciones de salud, así como la aplicación
de las medidas que se requieran ante situaciones de contingencia y urgencia derivadas
del acto autorizado.</p>

<p>De igual manera, se me informó que en cualquier momento y sin necesidad de explicación
alguna puedo renunciar por escrito a seguir recibiendo la atención médica en cuestión.</p>

<p>Atendiendo a los principios de confidencialidad, designo a
<strong>{{ campo.designado }}</strong> ({{ campo.parentesco }}) para que sea la única
persona que reciba información sobre mi estado de salud, diagnóstico, tratamiento y
pronóstico.</p>"""
        + SIGN_PATIENT_DOCTOR
    ),
}

CI_PARENTERAL = {
    "code": "CI-PAR",
    "version": 1,
    "family": CONSENTIMIENTO,
    "title": "Consentimiento informado para administración de medicamentos por vía parenteral",
    "description": "Autorización previa a la aplicación del tratamiento indicado",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "medicamento", "label": "Medicamento a administrar", "type": "text", "group": "Administración", "required": True, "wide": True},
        choice("via", "Vía de administración", "Administración", opts("Intramuscular", "Endovenosa", "Subcutánea", "Intradérmica"), "Intramuscular"),
        {"key": "indicado_por", "label": "Indicado por", "type": "text", "group": "Administración", "wide": True,
         "help": "Médico que prescribió el tratamiento, si no es quien firma el documento."},
        {"key": "testigo", "label": "Testigo", "type": "text", "group": "Testigo"},
        {"key": "testigo_documento", "label": "Documento del testigo", "type": "text", "group": "Testigo"},
    ],
    "body": (
        PLACE_AND_DATE
        + """<table class="doc-grid">
<tr><td class="k">Paciente</td><td>{{ paciente.nombre_completo }}</td>
    <td class="k">Historia</td><td>{{ paciente.historia }}</td></tr>
<tr><td class="k">Documento</td><td>{{ paciente.tipo_documento }} {{ paciente.documento }}</td>
    <td class="k">Hora</td><td>{{ fecha.hora }}</td></tr>
<tr><td class="k">Medicamento</td><td>{{ campo.medicamento }}</td>
    <td class="k">Vía</td><td>{{ campo.via }}</td></tr>
</table>

<p>Por medio de la presente constancia, en pleno uso de mis facultades mentales, otorgo en
forma libre mi consentimiento a {{ clinica.nombre }} y a su personal de salud para que, en
ejercicio legal de su profesión y de acuerdo con el procedimiento establecido, me practique
la administración del medicamento indicado por vía {{ campo.via|minus }}, en cumplimiento del
tratamiento farmacológico prescrito por {{ campo.indicado_por }}.</p>

<p>Entiendo que este procedimiento forma parte del tratamiento instaurado por el profesional
tratante para el manejo de mi enfermedad, y que tanto el médico como el personal de enfermería
poseen la idoneidad y el entrenamiento suficientes para su realización.</p>

<p>He sido informado(a) de que pueden presentarse reacciones no deseadas o complicaciones
inherentes a la aplicación de medicamentos por vía parenteral, tales como equimosis,
hematomas, neuropatías, intolerancia al medicamento, reacciones alérgicas u otras reacciones
propias del fármaco administrado.</p>

<p>Declaro conocer que la actividad médica no puede garantizar resultados, dados los múltiples
factores que inciden en la recuperación del estado de salud. Las posibilidades descritas me
han sido explicadas en lenguaje claro y sencillo, las he comprendido, he tenido la oportunidad
de recibir explicaciones satisfactorias y, en constancia de ello, firmo.</p>"""
        + """<div class="doc-signatures">
<div class="sign"><div class="line"></div><div class="role">Firma del paciente</div>
<div class="hint">{{ paciente.nombre_completo }} · {{ paciente.tipo_documento }} {{ paciente.documento }}</div></div>
<div class="sign"><div class="line"></div><div class="role">Firma del testigo</div>
<div class="hint">{{ campo.testigo }} · {{ campo.testigo_documento }}</div></div>
<div class="sign"><div class="line"></div><div class="role">Firma del profesional</div>
<div class="hint">{{ profesional.nombre }} · CMP {{ profesional.cmp }}</div></div>
</div>"""
    ),
}

CI_TOXICOLOGICO = {
    "code": "CI-TOX",
    "version": 1,
    "family": CONSENTIMIENTO,
    "title": "Consentimiento para la prueba de dosaje toxicológico de cocaína y marihuana",
    "description": "Consejería previa y autorización de la toma de muestra",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        choice("decision", "Decisión del usuario", "Decisión", opts("Autorizo", "No autorizo"), "Autorizo"),
        choice("muestra", "Muestra a tomar", "Decisión", opts("Sangre", "Orina"), "Sangre"),
        {"key": "consejero", "label": "Consejero(a) que informó", "type": "text", "group": "Decisión", "wide": True},
    ],
    "body": (
        PLACE_AND_DATE
        + """<p>Yo, <strong>{{ paciente.nombre_completo }}</strong>, identificado(a) con
{{ paciente.tipo_documento }} N.° {{ paciente.documento }}, habiendo recibido consejería e
información acerca de la prueba de dosaje toxicológico de cocaína y marihuana,
<strong>{{ campo.decision|minus }}</strong> que se me tome la muestra de
{{ campo.muestra|minus }} para el despistaje correspondiente.</p>

<p>Me comprometo a regresar para recibir la consejería posterior a la prueba y mis
resultados. La consejería estuvo a cargo de {{ campo.consejero }}.</p>"""
        + """<div class="doc-signatures">
<div class="sign"><div class="line"></div><div class="role">Firma del paciente</div>
<div class="hint">{{ paciente.nombre_completo }} · {{ paciente.tipo_documento }} {{ paciente.documento }}</div></div>
<div class="sign"><div class="line"></div><div class="role">Firma del consejero</div>
<div class="hint">{{ campo.consejero }}</div></div>
</div>"""
    ),
}

CI_INFORME_RADIOLOGICO = {
    "code": "CI-RAD",
    "version": 1,
    "family": CONSENTIMIENTO,
    "title": "Consentimiento informado para la entrega del informe radiológico",
    "description": "Alcance de la responsabilidad del establecimiento en la entrega",
    "study_type": "RAYOS_X",
    "requires_signature": True,
    "fields": [
        {"key": "placas", "label": "Placas radiográficas solicitadas", "type": "text", "group": "Solicitud", "required": True, "wide": True,
         "placeholder": "Radiografía de tórax PA y columna lumbar"},
        {"key": "finalidad", "label": "Finalidad declarada", "type": "text", "group": "Solicitud", "wide": True,
         "default": "Presentación ante el médico legista"},
    ],
    "body": (
        PLACE_AND_DATE
        + """<p>Yo, <strong>{{ paciente.nombre_completo }}</strong>, identificado(a) con
{{ paciente.tipo_documento }} N.° {{ paciente.documento }}, declaro haber sido informado(a)
por el personal del establecimiento acerca del informe radiológico que estoy solicitando,
correspondiente a: <strong>{{ campo.placas }}</strong>, con la finalidad de
{{ campo.finalidad|minus }}.</p>

<p>Asimismo, tengo conocimiento de que {{ clinica.nombre }} es responsable únicamente de la
entrega del informe radiológico; es decir, sus funciones concluyen con la lectura de las
placas por un médico especialista en radiología y la entrega oportuna del informe
correspondiente.</p>

<p>En tal sentido, {{ clinica.nombre }} no es parte de ningún proceso judicial seguido por mi
persona, por lo que no será notificado como parte del proceso en ninguna de sus categorías.</p>

<p>Finalmente, he formulado las preguntas que consideré oportunas, las cuales han sido
absueltas con respuestas que considero suficientes y aceptables. Por lo tanto, en forma
consciente y voluntaria doy mi consentimiento para que se me entreguen el informe radiológico
y las placas realizadas en {{ clinica.nombre }}.</p>"""
        + """<div class="doc-signatures">
<div class="sign"><div class="line"></div><div class="role">Firma del paciente</div>
<div class="hint">{{ paciente.nombre_completo }} · {{ paciente.tipo_documento }} {{ paciente.documento }}</div></div>
</div>"""
    ),
}

CI_TRASLADO = {
    "code": "CI-TRA",
    "version": 1,
    "family": CONSENTIMIENTO,
    "title": "Consentimiento de traslado",
    "description": "Autorización del paciente o de su familiar responsable",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "destino", "label": "Ciudad de destino", "type": "text", "group": "Traslado", "required": True, "wide": True},
        {"key": "motivo", "label": "Motivo del traslado", "type": "text", "group": "Traslado", "wide": True,
         "default": "Continuar con su tratamiento médico"},
        choice("autoriza", "¿Quién autoriza?", "Traslado", opts("El paciente", "Un familiar responsable"), "El paciente"),
        {"key": "familiar", "label": "Familiar responsable", "type": "text", "group": "Familiar responsable", "wide": True,
         "help": "Se llena solo si el paciente no está en condiciones de autorizar su traslado."},
        {"key": "familiar_documento", "label": "Documento del familiar", "type": "text", "group": "Familiar responsable"},
        {"key": "familiar_parentesco", "label": "Parentesco", "type": "text", "group": "Familiar responsable"},
        choice("estado", "Estado del paciente", "Familiar responsable", ESTADO_PACIENTE, "Estable"),
    ],
    "body": (
        PLACE_AND_DATE
        + """<h2>Autorización del paciente</h2>
<p>Yo, <strong>{{ paciente.nombre_completo }}</strong>, identificado(a) con
{{ paciente.tipo_documento }} N.° {{ paciente.documento }}, de {{ paciente.edad }}, con
domicilio en {{ paciente.direccion }}, en plena capacidad de mis facultades mentales y
considerando mi actual estado de salud, solicito y autorizo mi traslado a la ciudad de
<strong>{{ campo.destino }}</strong> para {{ campo.motivo|minus }}.</p>

<p>Por lo tanto, estoy de acuerdo y doy mi consentimiento para ser trasladado(a).</p>

<div class="doc-signatures">
<div class="sign"><div class="line"></div><div class="role">Firma del paciente</div>
<div class="hint">{{ paciente.nombre_completo }} · {{ paciente.tipo_documento }} {{ paciente.documento }}</div></div>
<div class="sign"><div class="line"></div><div class="role">Nombre y firma del médico</div>
<div class="hint">{{ profesional.nombre }} · CMP {{ profesional.cmp }}</div></div>
</div>

<p class="doc-note">La sección siguiente se llena únicamente cuando el usuario no tiene las
facultades mentales o físicas para autorizar su traslado. Autoriza en este documento:
<strong>{{ campo.autoriza }}</strong>.</p>

<h2>Autorización del familiar responsable</h2>
<p>Yo, <strong>{{ campo.familiar }}</strong>, con documento N.° {{ campo.familiar_documento }},
en calidad de {{ campo.familiar_parentesco }} del(la) paciente
<strong>{{ paciente.nombre_completo }}</strong>, solicito y autorizo su traslado a la ciudad de
<strong>{{ campo.destino }}</strong> para continuar con su tratamiento médico. Por lo tanto,
estoy de acuerdo y doy mi consentimiento para que sea trasladado(a).</p>

<p>Soy consciente de que el estado de salud del paciente es
<strong>{{ campo.estado|mayus }}</strong> y, en razón de ello, exonero de toda responsabilidad
al personal de la ambulancia y a {{ clinica.nombre }} si sobreviniera el deceso del paciente
durante el traslado. De ser el caso, el equipo de la ambulancia retornaría al paciente al
establecimiento de origen.</p>"""
        + """<div class="doc-signatures">
<div class="sign"><div class="line"></div><div class="role">Nombre y firma del familiar</div>
<div class="hint">{{ campo.familiar }} · {{ campo.familiar_parentesco }}</div></div>
</div>"""
    ),
}

DJ_RADIOLOGIA = {
    "code": "DJ-RX",
    "version": 1,
    "family": CONSENTIMIENTO,
    "title": "Declaración jurada para estudio radiológico",
    "description": "Fecha de última regla y autorización del procedimiento",
    "study_type": "RAYOS_X",
    "requires_signature": True,
    "fields": [
        {"key": "fur", "label": "Fecha de última regla", "type": "date", "group": "Declaración", "required": True},
        choice("gestacion", "¿Posibilidad de gestación?", "Declaración", opts("No", "Sí"), "No"),
        {"key": "estudio", "label": "Estudio radiológico solicitado", "type": "text", "group": "Declaración", "required": True, "wide": True},
    ],
    "body": (
        PLACE_AND_DATE
        + """<p>Yo, <strong>{{ paciente.nombre_completo }}</strong>, identificada con
{{ paciente.tipo_documento }} N.° {{ paciente.documento }}, declaro bajo juramento que
la fecha de mi última regla se inició el <strong>{{ campo.fur }}</strong> y que la
posibilidad de encontrarme gestando es: <strong>{{ campo.gestacion|mayus }}</strong>.</p>

<p>En tal sentido, exonero de responsabilidad alguna a {{ clinica.nombre }} y autorizo
que se me practique el procedimiento de radiología correspondiente:
<strong>{{ campo.estudio }}</strong>.</p>

<p>Declaro que la información consignada es verdadera y que he sido informada sobre los
riesgos que la exposición a radiación ionizante puede representar durante el embarazo.</p>"""
        + """<div class="doc-signatures">
<div class="sign"><div class="line"></div><div class="role">Firma de la paciente</div>
<div class="hint">{{ paciente.nombre_completo }} · {{ paciente.tipo_documento }} {{ paciente.documento }}</div></div>
</div>"""
    ),
}

EXONERACION = {
    "code": "EXO-RESP",
    "version": 1,
    "family": CONSENTIMIENTO,
    "title": "Exoneración de responsabilidad médica",
    "description": "Atención en establecimiento sin soporte para paciente crítico",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "declarante", "label": "Declarante", "type": "text", "group": "Declarante", "required": True, "wide": True,
         "help": "Deje el nombre del propio paciente si firma él mismo."},
        {"key": "declarante_documento", "label": "Documento del declarante", "type": "text", "group": "Declarante"},
        {"key": "declarante_relacion", "label": "En calidad de", "type": "text", "group": "Declarante", "default": "Paciente"},
        {"key": "condicion", "label": "Condición clínica informada", "type": "textarea", "group": "Declaración", "required": True, "wide": True},
    ],
    "body": (
        PLACE_AND_DATE
        + """<p>Yo, <strong>{{ campo.declarante }}</strong>, identificado(a) con documento
N.° {{ campo.declarante_documento }}, en calidad de {{ campo.declarante_relacion }} del(la)
paciente <strong>{{ paciente.nombre_completo }}</strong>
({{ paciente.tipo_documento }} {{ paciente.documento }}), declaro mediante la presente que:</p>

<ol>
<li>He sido informado(a) por el(la) médico tratante sobre el estado de salud y el
    diagnóstico respectivo: {{ campo.condicion|parrafos }}</li>
<li>He sido informado(a) sobre la evolución del cuadro clínico, sus probables
    complicaciones y las acciones que se deberían tomar para evitarlas.</li>
<li>He sido informado(a) de que {{ clinica.nombre }} es un establecimiento de salud de
    categoría {{ clinica.categoria }} y que no cuenta con el equipamiento ni el soporte
    para la atención de pacientes en estado crítico.</li>
</ol>

<p>De acuerdo con lo informado, he decidido que la atención se realice en
{{ clinica.nombre }}, asumiendo la responsabilidad por las complicaciones que puedan
generarse a causa del estado de salud descrito y de la infraestructura con la que cuenta
el establecimiento. Por tanto, libero de responsabilidad médico-legal al médico tratante
y a {{ clinica.nombre }} en caso se genere alguna situación adversa.</p>

<p>He leído cuidadosamente el presente documento, lo entiendo y lo firmo voluntariamente,
sin ningún tipo de sujeción.</p>"""
        + SIGN_PATIENT_DOCTOR
    ),
}

CI_MENOR = {
    "code": "CI-MEN",
    "version": 1,
    "family": CONSENTIMIENTO,
    "title": "Consentimiento informado para menor de edad",
    "description": "Autorización otorgada por el padre, la madre o el apoderado",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "apoderado", "label": "Padre, madre o apoderado", "type": "text", "group": "Apoderado", "required": True, "wide": True},
        {"key": "apoderado_documento", "label": "Documento de identidad del apoderado", "type": "text", "group": "Apoderado", "required": True},
        {"key": "parentesco", "label": "Parentesco con el menor", "type": "select", "group": "Apoderado",
         "options": opts("Padre", "Madre", "Tutor", "Apoderado"), "default": "Madre"},
        {"key": "apoderado_telefono", "label": "Teléfono del apoderado", "type": "text", "group": "Apoderado"},
        {"key": "procedimiento_menor", "label": "Procedimiento, examen o tratamiento", "type": "textarea",
         "group": "Procedimiento", "required": True, "wide": True},
        {"key": "riesgos_menor", "label": "Riesgos informados", "type": "textarea", "group": "Procedimiento", "wide": True},
    ],
    "body": (
        PLACE_AND_DATE
        + """<p>Yo, <strong>{{ campo.apoderado }}</strong>, identificado(a) con documento de
identidad N.° {{ campo.apoderado_documento }}, en mi condición de {{ campo.parentesco|minus }}
del menor <strong>{{ paciente.nombre_completo }}</strong>, de {{ paciente.edad }} de edad e
historia clínica N.° {{ paciente.historia }}, declaro que he recibido información clara y
en lenguaje sencillo sobre:</p>

<p style="padding-left:16px"><em>{{ campo.procedimiento_menor|parrafos }}</em></p>

<p><strong>Riesgos informados:</strong> {{ campo.riesgos_menor|parrafos }}</p>

<p>El(la) profesional <strong>{{ profesional.nombre }}</strong> (CMP {{ profesional.cmp }})
ha absuelto todas mis preguntas. Comprendo que la actividad médica no puede garantizar
resultados y que, de presentarse una situación de emergencia durante el procedimiento, el
equipo actuará conforme a la lex artis en beneficio del menor.</p>

<p>En pleno uso de mis facultades y de manera libre y voluntaria, <strong>AUTORIZO</strong>
que se realice el procedimiento descrito en {{ clinica.nombre }}. Cualquier comunicación
urgente puede dirigirse al teléfono {{ campo.apoderado_telefono }}.</p>"""
        + """<div class="doc-signatures">
<div class="sign"><div class="line"></div>
<div class="role">Padre, madre o apoderado</div>
<div class="hint">{{ campo.apoderado }} · {{ campo.apoderado_documento }}</div></div>
<div class="sign"><div class="line"></div><div class="role">Firma del médico</div>
<div class="hint">{{ profesional.nombre }} · CMP {{ profesional.cmp }}</div></div>
</div>"""
    ),
}

CI_QUIRURGICO = {
    "code": "CI-QX",
    "version": 1,
    "family": CONSENTIMIENTO,
    "title": "Consentimiento informado para acto quirúrgico y anestésico",
    "description": "Autorización de la intervención, la anestesia y las transfusiones",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "intervencion", "label": "Intervención quirúrgica propuesta", "type": "textarea",
         "group": "Intervención", "required": True, "wide": True},
        {"key": "diagnostico_qx", "label": "Diagnóstico que la motiva", "type": "text", "group": "Intervención", "required": True, "wide": True},
        choice("anestesia_ci", "Tipo de anestesia previsto", "Intervención",
               opts("Local", "Regional", "Raquídea", "General"), "Local"),
        {"key": "alternativas", "label": "Alternativas de tratamiento explicadas", "type": "textarea",
         "group": "Información", "default": "Tratamiento médico conservador y observación", "wide": True},
        {"key": "riesgos_qx", "label": "Riesgos propios de esta intervención", "type": "textarea",
         "group": "Información", "required": True, "wide": True},
        choice("transfusion", "Autoriza transfusión sanguínea de ser necesaria", "Información", opts("Sí", "No"), "Sí"),
        choice("ampliacion", "Autoriza ampliar el procedimiento ante un hallazgo imprevisto", "Información", opts("Sí", "No"), "Sí"),
        {"key": "acompanante", "label": "Familiar o acompañante responsable", "type": "text", "group": "Información", "wide": True},
    ],
    "body": (
        PLACE_AND_DATE
        + """<p>Yo, <strong>{{ paciente.nombre_completo }}</strong>, identificado(a) con
{{ paciente.tipo_documento }} N.° {{ paciente.documento }}, historia clínica N.°
{{ paciente.historia }}, declaro que el(la) profesional <strong>{{ profesional.nombre }}</strong>
(CMP {{ profesional.cmp }}) me ha explicado, en lenguaje claro y sencillo, que por el
diagnóstico de <strong>{{ campo.diagnostico_qx }}</strong> requiero la siguiente
intervención:</p>

<p style="padding-left:16px"><em>{{ campo.intervencion|parrafos }}</em></p>

<table class="doc-grid">
<tr><td class="k">Tipo de anestesia</td><td>{{ campo.anestesia_ci }}</td>
    <td class="k">Acompañante responsable</td><td>{{ campo.acompanante }}</td></tr>
</table>

<p><strong>Alternativas explicadas:</strong> {{ campo.alternativas|parrafos }}</p>
<p><strong>Riesgos de la intervención:</strong> {{ campo.riesgos_qx|parrafos }}</p>

<p>Se me ha informado además sobre los riesgos generales de todo acto quirúrgico y
anestésico: infección de la herida, sangrado, reacción adversa a los medicamentos y a la
anestesia, tromboembolismo y, excepcionalmente, complicaciones que pueden comprometer la
vida. Entiendo que la medicina no es una ciencia exacta y que no se me puede garantizar
un resultado.</p>

<table class="doc-grid">
<tr><td class="k">Autoriza transfusión sanguínea</td><td>{{ campo.transfusion }}</td>
    <td class="k">Autoriza ampliar el procedimiento</td><td>{{ campo.ampliacion }}</td></tr>
</table>

<p>He tenido la oportunidad de formular preguntas y todas han sido absueltas. En pleno uso
de mis facultades físicas y mentales, de manera libre y voluntaria, <strong>AUTORIZO</strong>
la realización de la intervención descrita y de la anestesia que requiera. Conozco que puedo
revocar este consentimiento en cualquier momento antes del procedimiento.</p>"""
        + SIGN_PATIENT_DOCTOR
    ),
}

AUTORIZACION_TRASLADO_PACIENTE = {
    "code": "CI-TRP",
    "version": 1,
    "family": CONSENTIMIENTO,
    "title": "Solicitud y autorización de traslado del propio paciente",
    "description": "El paciente, consciente y orientado, pide su traslado a otro establecimiento",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "destino_traslado", "label": "Establecimiento o ciudad de destino", "type": "text",
         "group": "Traslado", "required": True, "wide": True},
        {"key": "motivo_traslado", "label": "Motivo del traslado", "type": "textarea", "group": "Traslado", "required": True, "wide": True},
        choice("orientado", "Estado de conciencia", "Traslado", ORIENTADO, "Orientado"),
        {"key": "acompanante_traslado", "label": "Persona que lo acompaña", "type": "text", "group": "Traslado", "wide": True},
    ],
    "body": (
        PLACE_AND_DATE
        + """<p>Yo, <strong>{{ paciente.nombre_completo }}</strong>, identificado(a) con
{{ paciente.tipo_documento }} N.° {{ paciente.documento }}, de {{ paciente.edad }} de edad,
con domicilio en {{ paciente.direccion }}, encontrándome <strong>{{ campo.orientado|minus }}</strong>
en tiempo, espacio y persona, y en plena capacidad de mis facultades mentales, considerando
mi actual estado de salud:</p>

<p><strong>SOLICITO Y AUTORIZO</strong> mi traslado a
<strong>{{ campo.destino_traslado }}</strong> para continuar con mi tratamiento médico, por
el siguiente motivo:</p>

<p style="padding-left:16px"><em>{{ campo.motivo_traslado|parrafos }}</em></p>

<p>Estoy de acuerdo y doy mi consentimiento para ser trasladado(a), habiendo sido informado(a)
de los riesgos que el traslado implica en mi condición actual. Me acompaña durante el
traslado {{ campo.acompanante_traslado }}.</p>"""
        + SIGN_PATIENT_DOCTOR
    ),
}

ALTA_VOLUNTARIA = {
    "code": "ALTA-VOL",
    "version": 1,
    "family": ADMINISTRATIVO,
    "title": "Alta voluntaria",
    "description": "Egreso solicitado por el paciente contra opinión médica",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "fecha_ingreso", "label": "Fecha de ingreso", "type": "date", "group": "Egreso"},
        {"key": "diagnostico_ingreso", "label": "Diagnóstico de ingreso", "type": "text", "group": "Egreso", "wide": True},
        {"key": "diagnostico_egreso", "label": "Diagnóstico de egreso", "type": "text", "group": "Egreso", "required": True, "wide": True},
        {"key": "motivo", "label": "Motivo del egreso", "type": "textarea", "group": "Egreso", "required": True, "wide": True},
        {"key": "familiar", "label": "Familiar responsable", "type": "text", "group": "Egreso", "wide": True},
    ],
    "body": (
        PLACE_AND_DATE
        + """<table class="doc-grid">
<tr><td class="k">Paciente</td><td>{{ paciente.nombre_completo }}</td>
    <td class="k">Historia</td><td>{{ paciente.historia }}</td></tr>
<tr><td class="k">Fecha de ingreso</td><td>{{ campo.fecha_ingreso }}</td>
    <td class="k">Fecha de egreso</td><td>{{ fecha.hoy }}</td></tr>
<tr><td class="k">Dx. de ingreso</td><td>{{ campo.diagnostico_ingreso }}</td>
    <td class="k">Dx. de egreso</td><td>{{ campo.diagnostico_egreso }}</td></tr>
</table>

<p><strong>Motivo del egreso:</strong> {{ campo.motivo|parrafos }}</p>

<p>Por mi propia voluntad y no obstante la opinión del personal médico de
{{ clinica.nombre }}, he decidido solicitar mi <strong>ALTA VOLUNTARIA</strong> de este
establecimiento, motivo por el cual eximo de toda responsabilidad a {{ clinica.nombre }}
y a su personal por las consecuencias que pudieran sobrevenir a causa de mi
determinación.</p>"""
        + """<div class="doc-signatures">
<div class="sign"><div class="line"></div><div class="role">Paciente</div>
<div class="hint">{{ paciente.nombre_completo }}</div></div>
<div class="sign"><div class="line"></div><div class="role">Familiar responsable</div>
<div class="hint">{{ campo.familiar }}</div></div>
<div class="sign"><div class="line"></div><div class="role">Testigo</div><div class="hint">Documento de identidad</div></div>
<div class="sign"><div class="line"></div><div class="role">Médico tratante</div>
<div class="hint">{{ profesional.nombre }} · CMP {{ profesional.cmp }}</div></div>
</div>"""
    ),
}


HOJA_TRASLADO = {
    "code": "TRA-AMB",
    "version": 1,
    "family": ADMINISTRATIVO,
    "title": "Hoja de traslado en ambulancia",
    "description": "Servicio de ambulancia: ruta, tripulación y estado del paciente",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        choice("tipo_servicio", "Tipo de servicio", "Traslado", opts("Urbano", "Interprovincial"), "Urbano"),
        choice("via", "Vía", "Traslado", opts("Terrestre", "Fluvial", "Aérea"), "Terrestre"),
        {"key": "origen", "label": "Lugar donde se recoge al paciente", "type": "text", "group": "Traslado", "required": True, "wide": True,
         "placeholder": "Hospital de Satipo"},
        {"key": "destino", "label": "Lugar de destino", "type": "text", "group": "Traslado", "required": True, "wide": True},
        {"key": "hora_salida", "label": "Hora de salida", "type": "text", "group": "Traslado", "placeholder": "14:35"},
        {"key": "hora_llegada", "label": "Hora de llegada", "type": "text", "group": "Traslado", "placeholder": "15:20"},
        {"key": "hora_retorno", "label": "Hora de retorno", "type": "text", "group": "Traslado", "placeholder": "16:40"},
        {"key": "placa", "label": "Placa de la ambulancia", "type": "text", "group": "Tripulación"},
        {"key": "conductor1", "label": "Conductor 1", "type": "text", "group": "Tripulación", "wide": True},
        {"key": "conductor2", "label": "Conductor 2", "type": "text", "group": "Tripulación", "wide": True},
        {"key": "profesional_asiste", "label": "Profesional que asiste durante el traslado", "type": "text", "group": "Tripulación", "wide": True},
        choice("estado", "Estado del paciente", "Estado del paciente", ESTADO_PACIENTE, "Estable",),
        *[
            {
                "key": key,
                "label": label,
                "type": "select",
                "group": "Escala de Glasgow",
                "options": options,
                "default": options[0]["value"],
            }
            for key, label, options in (
                ("glasgow_ocular", "Apertura ocular", GLASGOW_OCULAR),
                ("glasgow_verbal", "Respuesta verbal", GLASGOW_VERBAL),
                ("glasgow_motora", "Respuesta motora", GLASGOW_MOTORA),
            )
        ],
        {
            "key": "glasgow",
            "label": "Glasgow total (sobre 15)",
            "type": "computed",
            "group": "Escala de Glasgow",
            "sum": ["glasgow_ocular", "glasgow_verbal", "glasgow_motora"],
            "help": "13 a 15 corresponde a TCE leve; 9 a 12, moderado; 8 o menos, grave.",
        },
        choice("severidad", "Interpretación", "Escala de Glasgow",
               opts("TCE leve", "TCE moderado", "TCE grave", "No aplica"), "No aplica"),
        {"key": "cie10", "label": "CIE-10", "type": "text", "group": "Indicación", "placeholder": "S06.0"},
        {"key": "justificacion", "label": "Justificación médica del traslado", "type": "textarea", "group": "Indicación", "required": True, "wide": True},
        {"key": "receptor", "label": "Persona que recibe al paciente", "type": "text", "group": "Recepción", "wide": True},
        {"key": "receptor_establecimiento", "label": "Establecimiento que recibe", "type": "text", "group": "Recepción", "wide": True},
    ],
    "body": (
        """<table class="doc-grid">
<tr><td class="k">Paciente</td><td>{{ paciente.nombre_completo }}</td>
    <td class="k">Historia</td><td>{{ paciente.historia }}</td></tr>
<tr><td class="k">Documento</td><td>{{ paciente.tipo_documento }} {{ paciente.documento }}</td>
    <td class="k">Edad</td><td>{{ paciente.edad }}</td></tr>
<tr><td class="k">Fecha</td><td>{{ fecha.hoy }}</td>
    <td class="k">Estado del paciente</td><td>{{ campo.estado }}</td></tr>
</table>

<h2>Traslado</h2>
<table class="doc-grid">
<tr><td class="k">Se recoge en</td><td>{{ campo.origen }}</td>
    <td class="k">Destino</td><td>{{ campo.destino }}</td></tr>
<tr><td class="k">Tipo de servicio</td><td>{{ campo.tipo_servicio }}</td>
    <td class="k">Vía</td><td>{{ campo.via }}</td></tr>
<tr><td class="k">Hora de salida</td><td>{{ campo.hora_salida }}</td>
    <td class="k">Hora de llegada</td><td>{{ campo.hora_llegada }}</td></tr>
<tr><td class="k">Hora de retorno</td><td colspan="3">{{ campo.hora_retorno }}</td></tr>
</table>

<h2>Ambulancia y tripulación</h2>
<table class="doc-grid">
<tr><td class="k">Placa</td><td colspan="3">{{ campo.placa }}</td></tr>
<tr><td class="k">Conductor 1</td><td colspan="3">{{ campo.conductor1 }}</td></tr>
<tr><td class="k">Conductor 2</td><td colspan="3">{{ campo.conductor2 }}</td></tr>
<tr><td class="k">Profesional que asiste</td><td colspan="3">{{ campo.profesional_asiste }}</td></tr>
</table>

<h2>Estado clínico</h2>
<table class="doc-table">
<tr><th>Apertura ocular</th><th>Respuesta verbal</th><th>Respuesta motora</th><th>Glasgow</th></tr>
<tr><td>{{ campo.glasgow_ocular }}</td><td>{{ campo.glasgow_verbal }}</td>
    <td>{{ campo.glasgow_motora }}</td><td><strong>{{ campo.glasgow }}/15</strong></td></tr>
</table>
<table class="doc-grid">
<tr><td class="k">Interpretación</td><td>{{ campo.severidad }}</td>
    <td class="k">CIE-10</td><td>{{ campo.cie10 }}</td></tr>
</table>

<h2>Justificación médica</h2>
<p>{{ campo.justificacion|parrafos }}</p>

<h2>Recepción</h2>
<table class="doc-grid">
<tr><td class="k">Recibe</td><td>{{ campo.receptor }}</td>
    <td class="k">Establecimiento</td><td>{{ campo.receptor_establecimiento }}</td></tr>
</table>"""
        + """<div class="doc-signatures">
<div class="sign"><div class="line"></div><div class="role">Médico que remite</div>
<div class="hint">{{ profesional.nombre }} · CMP {{ profesional.cmp }}</div></div>
<div class="sign"><div class="line"></div><div class="role">Persona que recibe</div>
<div class="hint">{{ campo.receptor }}</div></div>
</div>"""
    ),
}

ALTA_MEDICA = {
    "code": "ALTA-MED",
    "version": 1,
    "family": ADMINISTRATIVO,
    "title": "Alta médica y epicrisis",
    "description": "Resumen del internamiento, diagnósticos de egreso e indicaciones",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "fecha_ingreso_alta", "label": "Fecha de ingreso", "type": "date", "group": "Internamiento"},
        measure("dias_estancia", "Días de estancia", "Internamiento"),
        {"key": "dx_ingreso", "label": "Diagnóstico de ingreso", "type": "text", "group": "Internamiento", "required": True, "wide": True},
        {"key": "resumen", "label": "Resumen de la evolución", "type": "textarea", "group": "Evolución", "required": True, "wide": True},
        {"key": "procedimientos_alta", "label": "Procedimientos realizados", "type": "textarea", "group": "Evolución", "default": "Ninguno", "wide": True},
        {"key": "examenes_alta", "label": "Exámenes auxiliares relevantes", "type": "textarea", "group": "Evolución", "default": "Ninguno", "wide": True},
        {"key": "dx_egreso", "label": "Diagnósticos de egreso", "type": "textarea", "group": "Egreso", "required": True, "wide": True},
        {"key": "cie10_alta", "label": "CIE-10", "type": "text", "group": "Egreso", "placeholder": "A09"},
        choice("condicion_egreso", "Condición al egreso", "Egreso",
               opts("Curado", "Mejorado", "Estacionario", "Referido", "Fallecido"), "Mejorado"),
        {"key": "tratamiento_alta", "label": "Tratamiento al alta", "type": "textarea", "group": "Indicaciones", "required": True, "wide": True},
        {"key": "recomendaciones", "label": "Recomendaciones y signos de alarma", "type": "textarea", "group": "Indicaciones", "required": True, "wide": True},
        {"key": "control_alta", "label": "Próximo control", "type": "date", "group": "Indicaciones"},
    ],
    "body": (
        HEADER_CLINICAL
        + """<table class="doc-grid">
<tr><td class="k">Fecha de ingreso</td><td>{{ campo.fecha_ingreso_alta }}</td>
    <td class="k">Fecha de egreso</td><td>{{ fecha.hoy }}</td></tr>
<tr><td class="k">Días de estancia</td><td>{{ campo.dias_estancia }}</td>
    <td class="k">Condición al egreso</td><td>{{ campo.condicion_egreso }}</td></tr>
<tr><td class="k">Diagnóstico de ingreso</td><td colspan="3">{{ campo.dx_ingreso }}</td></tr>
</table>

<h2>Resumen de la evolución</h2>
<p>{{ campo.resumen|parrafos }}</p>
<p><strong>Procedimientos realizados:</strong> {{ campo.procedimientos_alta|parrafos }}</p>
<p><strong>Exámenes auxiliares:</strong> {{ campo.examenes_alta|parrafos }}</p>

<h2>Diagnósticos de egreso</h2>
<p>{{ campo.dx_egreso|parrafos }}</p>
<p><strong>CIE-10:</strong> {{ campo.cie10_alta }}</p>

<h2>Indicaciones al alta</h2>
<p>{{ campo.tratamiento_alta|parrafos }}</p>
<p><strong>Recomendaciones y signos de alarma:</strong> {{ campo.recomendaciones|parrafos }}</p>
<p><strong>Próximo control:</strong> {{ campo.control_alta }}</p>"""
        + SIGN_DOCTOR
    ),
}

HOJA_REFERENCIA = {
    "code": "REF",
    "version": 1,
    "family": ADMINISTRATIVO,
    "title": "Hoja de referencia",
    "description": "Derivación del paciente a otro establecimiento de salud",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "establecimiento_destino", "label": "Establecimiento de destino", "type": "text",
         "group": "Referencia", "required": True, "wide": True},
        {"key": "servicio_destino", "label": "Servicio o especialidad de destino", "type": "text", "group": "Referencia", "required": True, "wide": True},
        choice("prioridad", "Prioridad", "Referencia", opts("Emergencia", "Urgencia", "Consulta externa"), "Consulta externa"),
        {"key": "motivo_referencia", "label": "Motivo de la referencia", "type": "textarea", "group": "Referencia", "required": True, "wide": True},
        {"key": "resumen_clinico", "label": "Resumen del cuadro clínico", "type": "textarea", "group": "Condición del paciente", "required": True, "wide": True},
        {"key": "funciones_vitales_ref", "label": "Funciones vitales al momento de la referencia", "type": "text",
         "group": "Condición del paciente", "placeholder": "PA 120/80 · FC 80 · FR 18 · T° 36,8 · SatO₂ 98 %", "wide": True},
        {"key": "dx_referencia", "label": "Diagnóstico presuntivo", "type": "text", "group": "Condición del paciente", "required": True, "wide": True},
        {"key": "cie10_ref", "label": "CIE-10", "type": "text", "group": "Condición del paciente", "placeholder": "K35"},
        {"key": "tratamiento_recibido", "label": "Tratamiento recibido", "type": "textarea", "group": "Condición del paciente", "default": "Ninguno", "wide": True},
        {"key": "examenes_adjuntos", "label": "Exámenes que se adjuntan", "type": "text", "group": "Condición del paciente", "default": "Ninguno", "wide": True},
        choice("acompanado", "Traslado acompañado por personal de salud", "Condición del paciente", SI_NO, "No"),
    ],
    "body": (
        HEADER_CLINICAL
        + """<h2>Establecimiento al que se refiere</h2>
<table class="doc-grid">
<tr><td class="k">Establecimiento</td><td>{{ campo.establecimiento_destino }}</td>
    <td class="k">Servicio</td><td>{{ campo.servicio_destino }}</td></tr>
<tr><td class="k">Prioridad</td><td>{{ campo.prioridad }}</td>
    <td class="k">Traslado acompañado</td><td>{{ campo.acompanado }}</td></tr>
</table>
<p>{{ campo.motivo_referencia|parrafos }}</p>

<h2>Condición del paciente</h2>
<table class="doc-grid">
<tr><td class="k">Diagnóstico</td><td>{{ campo.dx_referencia }}</td>
    <td class="k">CIE-10</td><td>{{ campo.cie10_ref }}</td></tr>
<tr><td class="k">Funciones vitales</td><td colspan="3">{{ campo.funciones_vitales_ref }}</td></tr>
</table>
<p>{{ campo.resumen_clinico|parrafos }}</p>
<p><strong>Tratamiento recibido:</strong> {{ campo.tratamiento_recibido|parrafos }}</p>
<p><strong>Se adjunta:</strong> {{ campo.examenes_adjuntos }}</p>"""
        + SIGN_DOCTOR
    ),
}

HOJA_INTERCONSULTA = {
    "code": "ICS",
    "version": 1,
    "family": ADMINISTRATIVO,
    "title": "Hoja de interconsulta",
    "description": "Solicitud a otra especialidad y espacio para su respuesta",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "especialidad_solicitada", "label": "Especialidad a la que se solicita", "type": "text",
         "group": "Solicitud", "required": True, "wide": True},
        {"key": "puesto_trabajo", "label": "Puesto de trabajo", "type": "text", "group": "Solicitud"},
        {"key": "motivo_interconsulta", "label": "Motivo de la interconsulta", "type": "textarea",
         "group": "Solicitud", "required": True, "wide": True},
        {"key": "resumen_interconsulta", "label": "Resumen clínico y exámenes relevantes", "type": "textarea",
         "group": "Solicitud", "wide": True},
        {"key": "evaluacion_respuesta", "label": "Evaluación del especialista", "type": "textarea", "group": "Respuesta", "wide": True},
        {"key": "diagnostico_respuesta", "label": "Diagnóstico", "type": "textarea", "group": "Respuesta", "wide": True},
        {"key": "indicaciones_respuesta", "label": "Indicaciones médicas", "type": "textarea", "group": "Respuesta", "wide": True},
        {"key": "restricciones", "label": "Restricciones laborales", "type": "text", "group": "Respuesta", "default": "Ninguna", "wide": True},
        {"key": "especialista", "label": "Especialista que responde", "type": "text", "group": "Respuesta", "wide": True},
    ],
    "body": (
        HEADER_CLINICAL
        + """<h2>Solicitud</h2>
<table class="doc-grid">
<tr><td class="k">Especialidad</td><td>{{ campo.especialidad_solicitada }}</td>
    <td class="k">Puesto de trabajo</td><td>{{ campo.puesto_trabajo }}</td></tr>
</table>
<p>{{ campo.motivo_interconsulta|parrafos }}</p>
<p>{{ campo.resumen_interconsulta|parrafos }}</p>

<h2>Respuesta a la interconsulta</h2>
<p><strong>Evaluación:</strong> {{ campo.evaluacion_respuesta|parrafos }}</p>
<p><strong>Diagnóstico:</strong> {{ campo.diagnostico_respuesta|parrafos }}</p>
<p><strong>Indicaciones médicas:</strong> {{ campo.indicaciones_respuesta|parrafos }}</p>
<p><strong>Restricciones laborales:</strong> {{ campo.restricciones }}</p>"""
        + """<div class="doc-signatures">
<div class="sign"><div class="line"></div><div class="role">Médico que solicita</div>
<div class="hint">{{ profesional.nombre }} · CMP {{ profesional.cmp }}</div></div>
<div class="sign"><div class="line"></div><div class="role">Especialista que responde</div>
<div class="hint">{{ campo.especialista }}</div></div>
</div>"""
    ),
}

CERTIFICADO_MEDICO = {
    "code": "CERT-MED",
    "version": 1,
    "family": ADMINISTRATIVO,
    "title": "Certificado médico",
    "description": "Constancia del estado de salud y del diagnóstico",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "hallazgos_cert", "label": "Hallazgos del examen clínico", "type": "textarea",
         "group": "Certificación", "required": True, "wide": True},
        {"key": "diagnostico_cert", "label": "Diagnóstico", "type": "text", "group": "Certificación", "required": True, "wide": True},
        {"key": "cie10_cert", "label": "CIE-10", "type": "text", "group": "Certificación", "placeholder": "Z00.0"},
        {"key": "finalidad", "label": "Finalidad del certificado", "type": "text", "group": "Certificación",
         "required": True, "placeholder": "Presentar ante su centro de trabajo", "wide": True},
        {"key": "observaciones_cert", "label": "Observaciones", "type": "textarea", "group": "Certificación", "default": "Ninguna", "wide": True},
    ],
    "body": (
        """<p>El profesional que suscribe <strong>CERTIFICA</strong> que
<strong>{{ paciente.nombre_completo }}</strong>, identificado(a) con
{{ paciente.tipo_documento }} N.° {{ paciente.documento }}, de {{ paciente.edad }} de edad,
ha sido evaluado(a) en {{ clinica.nombre }} el día {{ fecha.hoy }}, encontrándose lo
siguiente:</p>

<p>{{ campo.hallazgos_cert|parrafos }}</p>

<table class="doc-grid">
<tr><td class="k">Diagnóstico</td><td>{{ campo.diagnostico_cert }}</td>
    <td class="k">CIE-10</td><td>{{ campo.cie10_cert }}</td></tr>
</table>

<p><strong>Observaciones:</strong> {{ campo.observaciones_cert|parrafos }}</p>

<p>Se expide el presente certificado a solicitud del interesado, con la finalidad de
{{ campo.finalidad|minus }}, para los fines que estime conveniente.</p>"""
        + PLACE_AND_DATE
        + SIGN_DOCTOR
    ),
}

DESCANSO_MEDICO = {
    "code": "DESC-MED",
    "version": 1,
    "family": ADMINISTRATIVO,
    "title": "Certificado de descanso médico",
    "description": "Días de reposo indicados y fecha de reincorporación",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "diagnostico_descanso", "label": "Diagnóstico", "type": "text", "group": "Descanso", "required": True, "wide": True},
        {"key": "cie10_descanso", "label": "CIE-10", "type": "text", "group": "Descanso", "placeholder": "J06"},
        measure("dias_descanso", "Días de descanso", "Descanso"),
        {"key": "desde", "label": "Desde", "type": "date", "group": "Descanso", "required": True},
        {"key": "hasta", "label": "Hasta", "type": "date", "group": "Descanso", "required": True},
        choice("tipo_descanso", "Tipo de descanso", "Descanso",
               opts("Reposo domiciliario", "Reposo relativo", "Hospitalización"), "Reposo domiciliario"),
        {"key": "indicaciones_descanso", "label": "Indicaciones durante el descanso", "type": "textarea",
         "group": "Descanso", "wide": True},
    ],
    "body": (
        """<p>El profesional que suscribe <strong>CERTIFICA</strong> que
<strong>{{ paciente.nombre_completo }}</strong>, identificado(a) con
{{ paciente.tipo_documento }} N.° {{ paciente.documento }}, ha sido atendido(a) en
{{ clinica.nombre }} y, por el diagnóstico de <strong>{{ campo.diagnostico_descanso }}</strong>
(CIE-10 {{ campo.cie10_descanso }}), requiere <strong>{{ campo.dias_descanso }} día(s)</strong>
de {{ campo.tipo_descanso|minus }}.</p>

<table class="doc-grid">
<tr><td class="k">Desde</td><td>{{ campo.desde }}</td>
    <td class="k">Hasta</td><td>{{ campo.hasta }}</td></tr>
</table>

<p><strong>Indicaciones durante el descanso:</strong> {{ campo.indicaciones_descanso|parrafos }}</p>

<p>Se expide el presente certificado a solicitud del interesado para los fines que estime
conveniente.</p>"""
        + PLACE_AND_DATE
        + SIGN_DOCTOR
    ),
}

CERTIFICADO_LUCIDEZ = {
    "code": "CERT-LUC",
    "version": 1,
    "family": ADMINISTRATIVO,
    "title": "Certificado de lucidez mental",
    "description": "Evaluación psicológica de las capacidades mentales y la autonomía",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "grado_instruccion", "label": "Grado de instrucción", "type": "text", "group": "Datos de la evaluación"},
        {"key": "ocupacion_luc", "label": "Ocupación", "type": "text", "group": "Datos de la evaluación"},
        {"key": "motivo_evaluacion", "label": "Motivo de la evaluación", "type": "text", "group": "Datos de la evaluación",
         "default": "Diagnóstico de lucidez mental", "wide": True},
        {"key": "instrumentos", "label": "Instrumentos y técnicas aplicadas", "type": "textarea",
         "group": "Datos de la evaluación", "required": True, "wide": True},
        choice("orientacion", "Orientación en espacio, tiempo y persona", "Observación psicológica",
               opts("Conservada", "Alterada"), "Conservada"),
        choice("lenguaje", "Lenguaje", "Observación psicológica",
               opts("Claro y coherente", "Alterado"), "Claro y coherente"),
        choice("memoria", "Memoria a corto, mediano y largo plazo", "Observación psicológica",
               opts("Conservada", "Alterada"), "Conservada"),
        choice("autoestima", "Autoestima", "Observación psicológica", opts("Adecuada", "Disminuida"), "Adecuada"),
        choice("dificultad_visual", "Dificultad visual", "Observación psicológica", SI_NO, "No"),
        choice("dificultad_auditiva", "Dificultad auditiva", "Observación psicológica", SI_NO, "No"),
        {"key": "observaciones_luc", "label": "Observaciones de la evaluación", "type": "textarea",
         "group": "Observación psicológica", "wide": True},
        choice("resultado_lucidez", "Resultado", "Conclusión",
               opts("Presenta adecuada lucidez mental", "No presenta adecuada lucidez mental"),
               "Presenta adecuada lucidez mental"),
        {"key": "conclusiones_luc", "label": "Conclusiones", "type": "textarea", "group": "Conclusión", "required": True, "wide": True},
    ],
    "body": (
        """<table class="doc-grid">
<tr><td class="k">Evaluado(a)</td><td>{{ paciente.nombre_completo }}</td>
    <td class="k">Edad</td><td>{{ paciente.edad }}</td></tr>
<tr><td class="k">Documento</td><td>{{ paciente.tipo_documento }} {{ paciente.documento }}</td>
    <td class="k">Fecha de nacimiento</td><td>{{ paciente.fecha_nacimiento }}</td></tr>
<tr><td class="k">Grado de instrucción</td><td>{{ campo.grado_instruccion }}</td>
    <td class="k">Ocupación</td><td>{{ campo.ocupacion_luc }}</td></tr>
<tr><td class="k">Fecha de evaluación</td><td>{{ fecha.hoy }}</td>
    <td class="k">Motivo</td><td>{{ campo.motivo_evaluacion }}</td></tr>
</table>

<h2>Observación psicológica</h2>
<table class="doc-table">
<tr><th>Área evaluada</th><th>Hallazgo</th><th>Área evaluada</th><th>Hallazgo</th></tr>
<tr><td>Orientación</td><td>{{ campo.orientacion }}</td><td>Lenguaje</td><td>{{ campo.lenguaje }}</td></tr>
<tr><td>Memoria</td><td>{{ campo.memoria }}</td><td>Autoestima</td><td>{{ campo.autoestima }}</td></tr>
<tr><td>Dificultad visual</td><td>{{ campo.dificultad_visual }}</td>
    <td>Dificultad auditiva</td><td>{{ campo.dificultad_auditiva }}</td></tr>
</table>
<p>{{ campo.observaciones_luc|parrafos }}</p>

<h2>Instrumentos y técnicas aplicadas</h2>
<p>{{ campo.instrumentos|parrafos }}</p>

<h2>Conclusiones</h2>
<p>A la fecha de esta evaluación, el(la) evaluado(a)
<strong>{{ campo.resultado_lucidez|mayus }}</strong> en el desarrollo de sus capacidades
mentales y emocionales, por lo que se encuentra en condiciones de comprender y decidir
sobre los actos que realiza.</p>
<p>{{ campo.conclusiones_luc|parrafos }}</p>"""
        + PLACE_AND_DATE
        + """<div class="doc-signatures">
<div class="sign"><div class="line"></div>
<div class="role">Psicólogo(a) responsable</div>
<div class="hint">{{ profesional.nombre }} · Colegiatura {{ profesional.cmp }}</div></div>
</div>"""
    ),
}

CONSTANCIA_ATENCION = {
    "code": "CONS-ATE",
    "version": 1,
    "family": ADMINISTRATIVO,
    "title": "Constancia de atención",
    "description": "Acredita la fecha, la hora y el servicio en que se atendió al paciente",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "servicio_constancia", "label": "Servicio en que fue atendido", "type": "text",
         "group": "Atención", "required": True, "wide": True},
        {"key": "hora_ingreso_cons", "label": "Hora de ingreso", "type": "text", "group": "Atención", "placeholder": "08:20"},
        {"key": "hora_salida_cons", "label": "Hora de salida", "type": "text", "group": "Atención", "placeholder": "09:45"},
        {"key": "acompanante_cons", "label": "Persona que lo acompañó", "type": "text", "group": "Atención", "wide": True},
        {"key": "finalidad_cons", "label": "Finalidad de la constancia", "type": "text", "group": "Atención",
         "default": "Justificar su inasistencia", "wide": True},
    ],
    "body": (
        """<p>{{ clinica.nombre }} deja <strong>CONSTANCIA</strong> de que
<strong>{{ paciente.nombre_completo }}</strong>, identificado(a) con
{{ paciente.tipo_documento }} N.° {{ paciente.documento }}, fue atendido(a) en este
establecimiento el día {{ fecha.hoy }}.</p>

<table class="doc-grid">
<tr><td class="k">Servicio</td><td colspan="3">{{ campo.servicio_constancia }}</td></tr>
<tr><td class="k">Hora de ingreso</td><td>{{ campo.hora_ingreso_cons }}</td>
    <td class="k">Hora de salida</td><td>{{ campo.hora_salida_cons }}</td></tr>
<tr><td class="k">Acompañante</td><td colspan="3">{{ campo.acompanante_cons }}</td></tr>
</table>

<p>Se expide la presente constancia a solicitud del interesado, con la finalidad de
{{ campo.finalidad_cons|minus }}. No contiene información clínica, la cual es
confidencial y solo se entrega al propio paciente o a quien él autorice.</p>"""
        + PLACE_AND_DATE
        + SIGN_DOCTOR
    ),
}

ORDEN_EXAMENES = {
    "code": "ORD-EXA",
    "version": 1,
    "family": ADMINISTRATIVO,
    "title": "Orden de exámenes auxiliares",
    "description": "Solicitud de laboratorio, imágenes u otros apoyos al diagnóstico",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        {"key": "diagnostico_orden", "label": "Diagnóstico presuntivo", "type": "text", "group": "Solicitud", "required": True, "wide": True},
        {"key": "cie10_orden", "label": "CIE-10", "type": "text", "group": "Solicitud", "placeholder": "N39.0"},
        {"key": "laboratorio", "label": "Exámenes de laboratorio", "type": "textarea", "group": "Exámenes solicitados", "wide": True},
        {"key": "imagenes", "label": "Estudios de imágenes", "type": "textarea", "group": "Exámenes solicitados", "wide": True},
        {"key": "otros_examenes", "label": "Otros exámenes", "type": "textarea", "group": "Exámenes solicitados", "wide": True},
        {"key": "preparacion", "label": "Preparación que debe seguir el paciente", "type": "textarea",
         "group": "Indicaciones", "default": "Acudir en ayunas de 8 horas", "wide": True},
        choice("urgencia_orden", "Prioridad", "Indicaciones", opts("Rutina", "Urgente"), "Rutina"),
        {"key": "fecha_orden", "label": "Fecha sugerida para la toma de muestra", "type": "date", "group": "Indicaciones"},
    ],
    "body": (
        HEADER_CLINICAL
        + """<table class="doc-grid">
<tr><td class="k">Diagnóstico presuntivo</td><td>{{ campo.diagnostico_orden }}</td>
    <td class="k">CIE-10</td><td>{{ campo.cie10_orden }}</td></tr>
<tr><td class="k">Prioridad</td><td>{{ campo.urgencia_orden }}</td>
    <td class="k">Fecha sugerida</td><td>{{ campo.fecha_orden }}</td></tr>
</table>

<h2>Exámenes solicitados</h2>
<p><strong>Laboratorio:</strong> {{ campo.laboratorio|parrafos }}</p>
<p><strong>Imágenes:</strong> {{ campo.imagenes|parrafos }}</p>
<p><strong>Otros:</strong> {{ campo.otros_examenes|parrafos }}</p>

<h2>Preparación</h2>
<p>{{ campo.preparacion|parrafos }}</p>"""
        + SIGN_DOCTOR
    ),
}

COTIZACION_LENTES = {
    "code": "COT-LEN",
    "version": 1,
    "family": ADMINISTRATIVO,
    "title": "Hoja de cotización de lentes",
    "description": "Montura, lunas y monto total cotizado en óptica",
    "study_type": "OPTOMETRIA",
    "requires_signature": False,
    "fields": [
        {"key": "montura", "label": "Montura", "type": "textarea", "group": "Cotización", "required": True, "wide": True},
        {"key": "precio_montura", "label": "Precio de la montura (S/)", "type": "number", "group": "Cotización"},
        {"key": "lunas", "label": "Lunas", "type": "textarea", "group": "Cotización", "required": True, "wide": True},
        {"key": "precio_lunas", "label": "Precio de las lunas (S/)", "type": "number", "group": "Cotización"},
        {
            "key": "total",
            "label": "Monto total (S/)",
            "type": "computed",
            "group": "Cotización",
            "sum": ["precio_montura", "precio_lunas"],
        },
        measure("validez_cotizacion", "Validez de la cotización (días)", "Condiciones", "15"),
        {"key": "tiempo_entrega", "label": "Tiempo de entrega", "type": "text", "group": "Condiciones",
         "default": "5 días hábiles"},
        {"key": "observaciones_cot", "label": "Observaciones", "type": "textarea", "group": "Condiciones", "wide": True},
    ],
    "body": (
        """<table class="doc-grid">
<tr><td class="k">Cliente</td><td>{{ paciente.nombre_completo }}</td>
    <td class="k">Fecha</td><td>{{ fecha.hoy }}</td></tr>
<tr><td class="k">Documento</td><td>{{ paciente.tipo_documento }} {{ paciente.documento }}</td>
    <td class="k">Teléfono</td><td>{{ paciente.telefono }}</td></tr>
</table>

<h2>Cotización</h2>
<table class="doc-table">
<tr><th>Concepto</th><th>Detalle</th><th>Importe</th></tr>
<tr><td>Montura</td><td>{{ campo.montura }}</td><td>S/ {{ campo.precio_montura }}</td></tr>
<tr><td>Lunas</td><td>{{ campo.lunas }}</td><td>S/ {{ campo.precio_lunas }}</td></tr>
<tr><td colspan="2"><strong>Monto total</strong></td><td><strong>S/ {{ campo.total }}</strong></td></tr>
</table>

<table class="doc-grid">
<tr><td class="k">Validez de la cotización</td><td>{{ campo.validez_cotizacion }} días</td>
    <td class="k">Tiempo de entrega</td><td>{{ campo.tiempo_entrega }}</td></tr>
</table>
<p><strong>Observaciones:</strong> {{ campo.observaciones_cot|parrafos }}</p>

<p class="doc-note">Esta cotización no constituye comprobante de pago. Los precios pueden
variar si cambia la medida prescrita o el tipo de luna elegido.</p>"""
    ),
}

PAGARE = {
    "code": "PAGARE",
    "version": 1,
    "family": ADMINISTRATIVO,
    "title": "Pagaré",
    "description": "Título valor por las prestaciones de salud recibidas",
    "study_type": None,
    "requires_signature": True,
    "fields": [
        measure("monto", "Importe (S/)", "Obligación"),
        {"key": "monto_letras", "label": "Importe en letras", "type": "text", "group": "Obligación", "required": True, "wide": True},
        {"key": "vencimiento", "label": "Fecha de vencimiento", "type": "date", "group": "Obligación", "required": True},
        {"key": "emitente", "label": "Emitente", "type": "text", "group": "Emitente", "required": True, "wide": True},
        {"key": "emitente_documento", "label": "Documento de identidad del emitente", "type": "text", "group": "Emitente", "required": True},
        {"key": "emitente_telefono", "label": "Teléfono del emitente", "type": "text", "group": "Emitente"},
        {"key": "emitente_domicilio", "label": "Domicilio del emitente", "type": "text", "group": "Emitente", "wide": True},
        {"key": "aval", "label": "Aval permanente", "type": "text", "group": "Aval", "wide": True},
        {"key": "aval_documento", "label": "Documento de identidad del aval", "type": "text", "group": "Aval"},
        {"key": "aval_domicilio", "label": "Domicilio del aval", "type": "text", "group": "Aval", "wide": True},
    ],
    "body": (
        """<table class="doc-grid">
<tr><td class="k">Por S/</td><td><strong>{{ campo.monto }}</strong></td>
    <td class="k">Vence el</td><td>{{ campo.vencimiento }}</td></tr>
<tr><td class="k">Paciente atendido</td><td colspan="3">{{ paciente.nombre_completo }} ·
    historia clínica N.° {{ paciente.historia }}</td></tr>
</table>

<p>Debo y pagaré en la forma de vencimiento indicada, a la orden de
<strong>{{ clinica.nombre_legal }}</strong> ({{ clinica.nombre }}), en el domicilio de dicha
institución sito en {{ clinica.direccion }} o en el lugar donde se me presentara este
documento, la cantidad de <strong>{{ campo.monto_letras|mayus }} SOLES</strong>, valor de las
prestaciones de salud recibidas a mi entera satisfacción.</p>

<p>Queda estipulado que si no pagase al vencimiento abonaré por mora el interés legal
correspondiente, de conformidad con lo establecido en el artículo 1244° del Código Civil,
más las costas y costos judiciales, comisiones, gastos administrativos y notariales y otros
en los que {{ clinica.nombre_legal }} incurra como consecuencia de mi incumplimiento.</p>

<p>Las prórrogas de este pagaré, por su importe total o por cantidad menor, que
{{ clinica.nombre_legal }} tuviera a bien concederme podrán ser anotadas en este documento
sin que sea necesaria su suscripción. En caso de incumplir la obligación contenida en este
título, en virtud de lo establecido en los artículos 52° y 81° de la Ley N.° 27287, Ley de
Títulos Valores, libero a {{ clinica.nombre_legal }} de la formalidad del protesto.</p>

<table class="doc-grid">
<tr><td class="k">Emitente</td><td colspan="3">{{ campo.emitente }}</td></tr>
<tr><td class="k">Documento</td><td>{{ campo.emitente_documento }}</td>
    <td class="k">Teléfono</td><td>{{ campo.emitente_telefono }}</td></tr>
<tr><td class="k">Domicilio</td><td colspan="3">{{ campo.emitente_domicilio }}</td></tr>
</table>

<p>Quien suscribe como aval permanente se constituye en tal por la obligación cambiaria que
contrae el emitente con {{ clinica.nombre_legal }}, comprometiéndose a responder por la
cantidad adeudada e intereses, comisiones, impuestos y gastos que puedan devengarse, y
aceptando desde ahora las prórrogas que se anoten en este documento.</p>

<table class="doc-grid">
<tr><td class="k">Aval permanente</td><td colspan="3">{{ campo.aval }}</td></tr>
<tr><td class="k">Documento</td><td>{{ campo.aval_documento }}</td>
    <td class="k">Domicilio</td><td>{{ campo.aval_domicilio }}</td></tr>
</table>"""
        + PLACE_AND_DATE
        + """<div class="doc-signatures">
<div class="sign"><div class="line"></div><div class="role">Firma del emitente</div>
<div class="hint">{{ campo.emitente }} · {{ campo.emitente_documento }}</div></div>
<div class="sign"><div class="line"></div><div class="role">Firma del aval permanente</div>
<div class="hint">{{ campo.aval }} · {{ campo.aval_documento }}</div></div>
</div>"""
    ),
}


TEMPLATES: tuple[dict[str, Any], ...] = (
    ECO_ABDOMINAL,
    ECO_TIROIDES,
    ECO_OBSTETRICA,
    ECO_TRANSVAGINAL,
    ECO_MAMAS,
    ECO_RENAL,
    ECO_PELVICA,
    ECO_HISTEROSONOGRAFIA,
    ECO_MORFOLOGICA,
    ECO_PERFIL_BIOFISICO,
    ECO_DOPPLER,
    ECO_GEMELAR,
    ECO_PROSTATA,
    ECO_TESTICULAR,
    ECO_PARTES_BLANDAS,
    ECG,
    INFORME_RADIOLOGICO,
    INFORME_AUDIOMETRIA,
    INFORME_ESPIROMETRIA,
    LAB_HEMOGRAMA,
    LAB_ORINA,
    LAB_PARASITOLOGICO,
    LAB_BIOQUIMICA,
    LAB_LIPIDICO,
    LAB_HEPATICO,
    LAB_RENAL,
    LAB_TIROIDEO,
    LAB_GLICOSILADA,
    LAB_GRUPO,
    LAB_COAGULACION,
    LAB_VSG,
    LAB_PCR,
    LAB_RPR,
    LAB_VIH,
    LAB_HEPATITIS,
    LAB_DENGUE,
    LAB_HELICOBACTER,
    LAB_AGLUTINACIONES,
    LAB_EMBARAZO,
    LAB_UROCULTIVO,
    LAB_GRAM,
    LAB_BACILOSCOPIA,
    LAB_GOTA_GRUESA,
    LAB_HONGOS,
    LAB_LEISHMANIASIS,
    LAB_PROTEINURIA,
    FICHA_OPTOMETRIA,
    RECETA_LENTES,
    RECETA_MEDICA,
    FICHA_EPWORTH,
    RIESGO_QUIRURGICO,
    EVALUACION_PSICOSOMATICA,
    INFORME_PSICOLOGICO,
    TAMIZAJE_SRQ,
    HISTORIA_CLINICA_GENERAL,
    HISTORIA_CLINICA_GENERAL_V2,
    HISTORIA_RECIEN_NACIDO,
    FICHA_TERAPIA_FISICA,
    CONTROL_TERAPIA,
    EVOLUCION_HOSPITALIZACION,
    REPORTE_OPERATORIO,
    CUIDADOS_URPA,
    HISTORIA_EMERGENCIA,
    HISTORIA_GINECO_OBSTETRICA,
    HISTORIA_GINECO_CONTINUADORA,
    HISTORIA_ODONTOLOGICA,
    HISTORIA_BOTOX,
    HISTORIA_PLASMA,
    ATENCION_INTEGRAL_NINO,
    TAMIZAJE_VIOLENCIA_INFANTIL,
    CI_PROCEDIMIENTOS,
    CI_VIH,
    CI_HOSPITALIZACION,
    CI_PARENTERAL,
    CI_TOXICOLOGICO,
    CI_INFORME_RADIOLOGICO,
    CI_TRASLADO,
    CI_MENOR,
    CI_QUIRURGICO,
    AUTORIZACION_TRASLADO_PACIENTE,
    DJ_RADIOLOGIA,
    EXONERACION,
    ALTA_VOLUNTARIA,
    ALTA_MEDICA,
    HOJA_TRASLADO,
    HOJA_REFERENCIA,
    HOJA_INTERCONSULTA,
    CERTIFICADO_MEDICO,
    DESCANSO_MEDICO,
    CERTIFICADO_LUCIDEZ,
    CONSTANCIA_ATENCION,
    ORDEN_EXAMENES,
    COTIZACION_LENTES,
    PAGARE,
)


def seed_document_templates(db: Session) -> None:
    """Carga las plantillas que falten, respetando el versionado por código.

    Es idempotente: una versión ya presente no se toca, de modo que un ajuste
    manual hecho en producción no se pisa al reiniciar. Publicar una versión
    nueva desactiva las anteriores del mismo código.
    """
    repo = DocumentTemplateRepository(db)
    created = 0

    for spec in TEMPLATES:
        if repo.get_version(spec["code"], spec["version"]) is not None:
            continue

        template = DocumentTemplate(**spec, is_active=True)
        for problem in _validate(template):
            logger.warning("Plantilla %s: %s", template.code, problem)

        for older in repo.versions_of(spec["code"]):
            older.is_active = False
        db.add(template)
        # La sesión no hace autoflush, así que sin este flush una base recién
        # creada insertaría de golpe dos versiones del mismo código y las dos
        # quedarían activas: la plantilla saldría duplicada en el selector.
        db.flush()
        created += 1

    if created:
        db.commit()
        logger.info("Plantillas de documentos cargadas: %d", created)


def _validate(template: DocumentTemplate) -> list[str]:
    """Avisa si el cuerpo y el esquema de campos no se corresponden."""
    from app.core.templating import field_keys

    declared = {field["key"] for field in template.fields}
    used = field_keys(template.body)
    return [f"campo usado sin definir: {key}" for key in sorted(used - declared)] + [
        f"campo definido y no usado: {key}" for key in sorted(declared - used)
    ]

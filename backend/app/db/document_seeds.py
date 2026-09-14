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
from typing import Any

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
    FICHA_OPTOMETRIA,
    RECETA_LENTES,
    RECETA_MEDICA,
    FICHA_EPWORTH,
    RIESGO_QUIRURGICO,
    EVALUACION_PSICOSOMATICA,
    INFORME_PSICOLOGICO,
    CI_PROCEDIMIENTOS,
    CI_VIH,
    CI_HOSPITALIZACION,
    CI_PARENTERAL,
    CI_TOXICOLOGICO,
    CI_INFORME_RADIOLOGICO,
    CI_TRASLADO,
    DJ_RADIOLOGIA,
    EXONERACION,
    ALTA_VOLUNTARIA,
    HOJA_TRASLADO,
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

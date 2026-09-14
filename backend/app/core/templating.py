"""Motor de plantillas de los documentos clínicos (opción B del análisis).

El cuerpo de una plantilla es HTML con marcadores `{{ ámbito.campo }}`. El motor
solo sustituye texto: no evalúa expresiones ni ejecuta código, de modo que
ampliar el catálogo de plantillas nunca abre una vía de ejecución. Todo valor
sustituido se escapa antes de insertarse, así un dato del paciente jamás puede
alterar la estructura del documento.

Un marcador sin valor no desaparece: se imprime como una línea punteada, igual
que el espacio en blanco del formato en papel al que reemplaza.

Un valor puede ser una lista de líneas ya compuestas por el servicio (los
medicamentos de una receta, por ejemplo). Con el filtro `|lista` se imprime
numerada; sin él, unida por punto y coma. En ambos casos cada línea se escapa
por separado, así que la estructura HTML sigue viniendo solo de la plantilla.
"""

import html
import re
from collections.abc import Mapping
from typing import Any

# {{ paciente.nombre_completo }} · {{ campo.conclusion|mayus }}
_PLACEHOLDER = re.compile(
    r"\{\{\s*(?P<scope>[a-z_]+)\.(?P<key>[a-z0-9_]+)\s*(?:\|\s*(?P<filter>[a-z_]+)\s*)?\}\}"
)

# Ámbito de los campos que captura el usuario; el resto lo aporta el sistema.
FIELD_SCOPE = "campo"

# Espacio a rellenar a mano cuando el dato no se registró en el sistema.
BLANK_MARK = '<span class="doc-blank"></span>'

_BLOCK_BREAKS = re.compile(r"</(?:p|div|tr|li|h[1-6]|section|article|header|footer)>|<br\s*/?>", re.I)
_TAGS = re.compile(r"<[^>]+>")
_BLANK_LINES = re.compile(r"\n{3,}")

MONTHS: tuple[str, ...] = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "setiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


def _as_text(value: Any) -> str:
    """Normaliza a texto el valor guardado en el JSON del documento."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "; ".join(_as_text(item) for item in value if _as_text(item))
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _apply_filter(name: str | None, raw: str) -> str:
    """Los filtros operan sobre el texto plano; el escape ocurre después."""
    if name == "mayus":
        return raw.upper()
    if name == "minus":
        return raw.lower()
    if name == "titulo":
        return raw.title()
    return raw


def _escape(raw: str, filter_name: str | None) -> str:
    escaped = html.escape(raw)
    if filter_name == "parrafos":
        # El salto de línea de un textarea se conserva en el documento impreso.
        return escaped.replace("\n", "<br />")
    return escaped


def _render_list(items: Any) -> str:
    """Lista numerada a partir de una secuencia de líneas ya compuestas."""
    entries = [_as_text(item) for item in items]
    visible = [html.escape(entry) for entry in entries if entry]
    if not visible:
        return BLANK_MARK
    return "<ol>" + "".join(f"<li>{entry}</li>" for entry in visible) + "</ol>"


def render(body: str, context: Mapping[str, Mapping[str, Any]]) -> str:
    """Sustituye los marcadores de `body` con los valores de `context`."""

    def _replace(match: re.Match[str]) -> str:
        scope = context.get(match.group("scope"))
        value = scope.get(match.group("key")) if scope else None
        filter_name = match.group("filter")

        if filter_name == "lista":
            return _render_list(value if isinstance(value, (list, tuple)) else [value])

        raw = _as_text(value)
        if not raw:
            return BLANK_MARK
        return _escape(_apply_filter(filter_name, raw), filter_name)

    return _PLACEHOLDER.sub(_replace, body)


def field_keys(body: str) -> set[str]:
    """Claves del ámbito `campo` usadas por la plantilla.

    Permite verificar, al sembrar el catálogo, que todo marcador editable tenga
    su definición en el esquema de campos y viceversa.
    """
    return {
        match.group("key")
        for match in _PLACEHOLDER.finditer(body)
        if match.group("scope") == FIELD_SCOPE
    }


def to_plain_text(markup: str) -> str:
    """Versión en texto plano del documento, para volcarla al informe del estudio."""
    text = _BLOCK_BREAKS.sub("\n", markup)
    text = _TAGS.sub("", text)
    text = html.unescape(text)
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return _BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()


# --- Presentación ---------------------------------------------------------
# Hoja A4 común a todos los documentos: la identidad se define una sola vez y
# las plantillas solo aportan su contenido. Todo selector cuelga de `.doc` para
# que la hoja no altere la aplicación cuando se muestra la vista previa.
STYLESHEET = """
@page { size: A4; margin: 14mm 15mm 16mm; }
.doc {
  --doc-ink: #24312f; --doc-soft: #5e706d; --doc-rule: #c4d9d5; --doc-brand: #2f8f84;
  max-width: 190mm; margin: 0 auto; padding: 10mm 11mm 12mm; background: #fff;
  color: var(--doc-ink); font-family: "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 10.5pt; line-height: 1.45;
}
.doc * { box-sizing: border-box; }
.doc-head { display: flex; align-items: center; gap: 12px; border-bottom: 2px solid var(--doc-brand); padding-bottom: 8px; }
.doc-head img { height: 52px; width: auto; }
.doc-head .doc-identity { flex: 1; min-width: 0; }
.doc-head .doc-name { font-size: 13pt; font-weight: 700; letter-spacing: .01em; color: var(--doc-brand); }
.doc-head .doc-meta { font-size: 8.5pt; color: var(--doc-soft); line-height: 1.35; }
.doc-title { margin: 14px 0 10px; font-size: 12.5pt; font-weight: 700; text-align: center; text-transform: uppercase; letter-spacing: .04em; }
.doc-body { text-align: justify; }
.doc-body p { margin: 0 0 7px; }
.doc-body h2 { margin: 12px 0 5px; font-size: 10.5pt; font-weight: 700; text-transform: uppercase; letter-spacing: .03em; color: var(--doc-brand); border-bottom: 1px solid var(--doc-rule); padding-bottom: 2px; }
.doc-body ol, .doc-body ul { margin: 0 0 8px; padding-left: 18px; }
.doc-body li { margin-bottom: 3px; }
.doc-blank { display: inline-block; min-width: 120px; border-bottom: 1px dotted var(--doc-soft); vertical-align: baseline; }
.doc-grid { width: 100%; border-collapse: collapse; margin-bottom: 8px; }
.doc-grid td { padding: 2.5px 6px 2.5px 0; vertical-align: top; }
.doc-grid td.k { width: 1%; white-space: nowrap; font-weight: 600; color: var(--doc-soft); text-transform: uppercase; font-size: 8.5pt; letter-spacing: .03em; }
.doc-table { width: 100%; border-collapse: collapse; margin: 6px 0 10px; font-size: 9.5pt; }
.doc-table th, .doc-table td { border: 1px solid var(--doc-rule); padding: 4px 6px; text-align: left; }
.doc-table th { background: #eef7f6; font-weight: 600; text-transform: uppercase; font-size: 8.5pt; letter-spacing: .03em; }
.doc-note { margin-top: 10px; padding: 6px 9px; background: #f3f8f7; border-left: 3px solid var(--doc-brand); font-size: 9pt; color: var(--doc-soft); }
.doc-signatures { display: flex; flex-wrap: wrap; gap: 18px; margin-top: 26px; page-break-inside: avoid; }
.doc-signatures .sign { flex: 1 1 40%; text-align: center; font-size: 9pt; }
.doc-signatures .sign .line { border-top: 1px solid var(--doc-ink); margin: 34px 8px 4px; }
.doc-signatures .sign .role { font-weight: 600; text-transform: uppercase; letter-spacing: .03em; }
.doc-signatures .sign .hint { color: var(--doc-soft); font-size: 8pt; }
.doc-foot { margin-top: 16px; padding-top: 6px; border-top: 1px solid var(--doc-rule); font-size: 7.5pt; color: var(--doc-soft); text-align: center; line-height: 1.4; }
@media print {
  .doc { max-width: none; margin: 0; padding: 0; font-size: 10pt; box-shadow: none; }
  .doc-body { orphans: 3; widows: 3; }
}
"""


def _identity_lines(clinic: Mapping[str, Any]) -> str:
    """Líneas de contacto del membrete, omitiendo los datos no configurados."""
    location = " · ".join(
        part for part in (clinic.get("direccion"), clinic.get("ubicacion")) if part
    )
    contact = " · ".join(
        f"{label} {value}"
        for label, value in (
            ("Tel.", clinic.get("telefono")),
            ("WhatsApp", clinic.get("whatsapp")),
            ("", clinic.get("correo")),
        )
        if value
    )
    registry = " · ".join(
        f"{label} {value}"
        for label, value in (
            ("RUC", clinic.get("ruc")),
            ("Categoría", clinic.get("categoria")),
            ("Cód. RENIPRESS", clinic.get("codigo_renipress")),
        )
        if value
    )
    return "".join(
        f"<div>{html.escape(line)}</div>" for line in (location, contact, registry) if line
    )


def wrap_document(
    *,
    title: str,
    body_html: str,
    context: Mapping[str, Mapping[str, Any]],
    logo_src: str | None = None,
) -> str:
    """Compone la hoja final: membrete, título, cuerpo y pie institucional.

    `body_html` ya viene renderizado y escapado por `render`; el resto se escapa
    aquí. Es el único lugar donde se define la identidad impresa del policlínico.
    """
    clinic = context.get("clinica", {})
    logo = f'<img src="{html.escape(logo_src)}" alt="" />' if logo_src else ""
    footer = clinic.get("pie") or clinic.get("nombre_legal") or clinic.get("nombre") or ""

    return (
        f"<style>{STYLESHEET}</style>"
        '<article class="doc">'
        f'<header class="doc-head">{logo}'
        '<div class="doc-identity">'
        f'<div class="doc-name">{html.escape(str(clinic.get("nombre") or ""))}</div>'
        f'<div class="doc-meta">{_identity_lines(clinic)}</div>'
        "</div></header>"
        f'<h1 class="doc-title">{html.escape(title)}</h1>'
        f'<section class="doc-body">{body_html}</section>'
        f'<footer class="doc-foot">{html.escape(str(footer))}</footer>'
        "</article>"
    )

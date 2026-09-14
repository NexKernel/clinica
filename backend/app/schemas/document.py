from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.document import DocumentFamily
from app.schemas.patient import PatientSummary
from app.schemas.types import LocalDatetime


class TemplateOption(BaseModel):
    value: str
    label: str


class TemplateField(BaseModel):
    """Definición de un campo editable de la plantilla.

    `type` gobierna el control que dibuja el cliente: text, textarea, number,
    date, select, boolean o computed. Un campo `computed` no se escribe: su
    valor es la suma de las claves indicadas en `sum` (escalas con puntaje).
    """

    key: str
    label: str
    type: str = "text"
    group: str | None = None
    default: Any = None
    placeholder: str | None = None
    help: str | None = None
    options: list[TemplateOption] | None = None
    sum: list[str] | None = None
    required: bool = False
    wide: bool = False


class TemplateListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    version: int
    family: str
    family_label: str
    title: str
    description: str | None
    requires_signature: bool
    study_type: str | None
    field_count: int


class TemplateRead(TemplateListItem):
    fields: list[TemplateField]


class DocumentBase(BaseModel):
    patient_id: int
    encounter_id: int | None = None
    study_id: int | None = None
    practitioner_id: int | None = None
    data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("data")
    @classmethod
    def _clean(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Descarta los campos vacíos: un dato ausente se imprime en blanco."""
        return {
            key: (" ".join(item.split()) if isinstance(item, str) else item)
            for key, item in value.items()
            if item is not None and (not isinstance(item, str) or item.strip())
        }


class DocumentCreate(DocumentBase):
    """Emisión de un documento a partir de una plantilla del catálogo."""

    template_code: str = Field(min_length=2, max_length=32)


class DocumentUpdate(DocumentBase):
    """Corrección de un documento aún en borrador."""


class DocumentVoid(BaseModel):
    reason: str = Field(min_length=4, max_length=255)


class DocumentListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str
    patient_id: int
    patient_name: str
    template_code: str
    template_version: int
    family: str
    family_label: str
    title: str
    status: str
    status_label: str
    practitioner_name: str | None
    study_id: int | None
    encounter_id: int | None
    issued_at: LocalDatetime | None
    created_at: LocalDatetime


class DocumentDetail(DocumentListItem):
    """Documento tal como está guardado, sin la definición de sus campos."""

    template_id: int
    practitioner_id: int | None
    data: dict[str, Any]
    void_reason: str | None
    voided_at: LocalDatetime | None
    is_draft: bool
    is_issued: bool
    patient: PatientSummary


class DocumentRead(DocumentDetail):
    """Detalle más los campos de la versión de plantilla con la que se llenó.

    El formulario del cliente se arma con `fields`, de modo que agregar un
    formato al catálogo no obliga a tocar el frontend.
    """

    fields: list[TemplateField]


class DocumentPreview(BaseModel):
    """Hoja lista para mostrar o imprimir.

    En borrador se rearma con la plantilla vigente; una vez emitido devuelve el
    HTML congelado al momento de la firma.
    """

    id: int
    number: str
    title: str
    status: str
    is_issued: bool
    html: str


class DocumentFamilyOption(BaseModel):
    value: DocumentFamily
    label: str

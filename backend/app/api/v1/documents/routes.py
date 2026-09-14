from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DbSession, PageParams, require_manage, require_view
from app.core.permissions import ModuleCode
from app.models import User
from app.models.document import DOCUMENT_FAMILY_LABELS, ClinicalDocument, DocumentFamily
from app.schemas.common import OperationResult, Page
from app.schemas.document import (
    DocumentCreate,
    DocumentDetail,
    DocumentFamilyOption,
    DocumentListItem,
    DocumentPreview,
    DocumentRead,
    DocumentUpdate,
    DocumentVoid,
    TemplateListItem,
    TemplateRead,
)
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])

Viewer = Annotated[User, Depends(require_view(ModuleCode.DOCUMENTS))]
Manager = Annotated[User, Depends(require_manage(ModuleCode.DOCUMENTS))]


def _read(service: DocumentService, document: ClinicalDocument) -> DocumentRead:
    """Une el documento con la definición de campos de su versión de plantilla."""
    detail = DocumentDetail.model_validate(document)
    return DocumentRead(**detail.model_dump(), fields=service.fields_of(document))


@router.get("/families", response_model=list[DocumentFamilyOption])
def list_families(current_user: Viewer) -> list[DocumentFamilyOption]:
    return [
        DocumentFamilyOption(value=family, label=DOCUMENT_FAMILY_LABELS[family.value])
        for family in DocumentFamily
    ]


@router.get("/templates", response_model=list[TemplateListItem])
def list_templates(
    db: DbSession,
    current_user: Viewer,
    family: Annotated[str | None, Query(max_length=20)] = None,
) -> list[TemplateListItem]:
    templates = DocumentService(db).list_templates(family)
    return [TemplateListItem.model_validate(item) for item in templates]


@router.get("/templates/{code}", response_model=TemplateRead)
def get_template(code: str, db: DbSession, current_user: Viewer) -> TemplateRead:
    return TemplateRead.model_validate(DocumentService(db).get_template(code))


@router.get("", response_model=Page[DocumentListItem])
def list_documents(
    db: DbSession,
    current_user: Viewer,
    pagination: PageParams,
    search: Annotated[str | None, Query(max_length=120)] = None,
    patient_id: Annotated[int | None, Query()] = None,
    family: Annotated[str | None, Query(max_length=20)] = None,
    document_status: Annotated[str | None, Query(alias="status", max_length=16)] = None,
    template_code: Annotated[str | None, Query(max_length=32)] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> Page[DocumentListItem]:
    items, total = DocumentService(db).list_documents(
        term=search,
        patient_id=patient_id,
        family=family,
        status=document_status,
        template_code=template_code,
        date_from=date_from,
        date_to=date_to,
        pagination=pagination,
    )
    return Page[DocumentListItem](
        items=[DocumentListItem.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/patient/{patient_id}", response_model=list[DocumentListItem])
def patient_documents(
    patient_id: int, db: DbSession, current_user: Viewer
) -> list[DocumentListItem]:
    items = DocumentService(db).history_for_patient(patient_id)
    return [DocumentListItem.model_validate(item) for item in items]


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document(payload: DocumentCreate, db: DbSession, current_user: Manager) -> DocumentRead:
    service = DocumentService(db)
    return _read(service, service.create(payload, current_user))


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: int, db: DbSession, current_user: Viewer) -> DocumentRead:
    service = DocumentService(db)
    return _read(service, service.get(document_id))


@router.put("/{document_id}", response_model=DocumentRead)
def update_document(
    document_id: int, payload: DocumentUpdate, db: DbSession, current_user: Manager
) -> DocumentRead:
    service = DocumentService(db)
    return _read(service, service.update(document_id, payload))


@router.get("/{document_id}/preview", response_model=DocumentPreview)
def preview_document(document_id: int, db: DbSession, current_user: Viewer) -> DocumentPreview:
    """Hoja lista para imprimir; el borrador se rearma en cada consulta."""
    service = DocumentService(db)
    document = service.get(document_id)
    return DocumentPreview(
        id=document.id,
        number=document.number,
        title=document.title,
        status=document.status,
        is_issued=document.is_issued,
        html=service.preview(document),
    )


@router.post("/{document_id}/issue", response_model=DocumentRead)
def issue_document(document_id: int, db: DbSession, current_user: Manager) -> DocumentRead:
    """Emite el documento: congela su contenido y lo deja como constancia."""
    service = DocumentService(db)
    return _read(service, service.issue(document_id, current_user))


@router.post("/{document_id}/void", response_model=DocumentRead)
def void_document(
    document_id: int, payload: DocumentVoid, db: DbSession, current_user: Manager
) -> DocumentRead:
    service = DocumentService(db)
    return _read(service, service.void(document_id, payload.reason))


@router.delete("/{document_id}", response_model=OperationResult)
def delete_document(document_id: int, db: DbSession, current_user: Manager) -> OperationResult:
    DocumentService(db).delete(document_id)
    return OperationResult(detail="Borrador eliminado")

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.api.deps import DbSession, PageParams, require_manage, require_view
from app.core.permissions import ModuleCode
from app.models import User
from app.schemas.common import OperationResult, Page
from app.schemas.study import (
    AttachmentRead,
    ShareLink,
    SharedStudy,
    StudyCreate,
    StudyListItem,
    StudyRead,
    StudyResultWrite,
    StudyStatusChange,
    StudyUpdate,
)
from app.services.exceptions import NotFoundError
from app.services.study_service import StudyService

router = APIRouter(prefix="/studies", tags=["studies"])

Viewer = Annotated[User, Depends(require_view(ModuleCode.STUDIES))]
Manager = Annotated[User, Depends(require_manage(ModuleCode.STUDIES))]


@router.get("", response_model=Page[StudyListItem])
def list_studies(
    db: DbSession,
    current_user: Viewer,
    pagination: PageParams,
    search: Annotated[str | None, Query(max_length=120)] = None,
    patient_id: Annotated[int | None, Query()] = None,
    study_type: Annotated[str | None, Query(max_length=20)] = None,
    study_status: Annotated[str | None, Query(alias="status", max_length=16)] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> Page[StudyListItem]:
    items, total = StudyService(db).list_studies(
        term=search,
        patient_id=patient_id,
        study_type=study_type,
        status=study_status,
        date_from=date_from,
        date_to=date_to,
        pagination=pagination,
    )
    return Page[StudyListItem](
        items=[StudyListItem.model_validate(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/shared/{token}", response_model=SharedStudy, tags=["public"])
def shared_study(token: str, db: DbSession) -> SharedStudy:
    """Consulta pública del resultado mediante el enlace enviado al paciente."""
    _, shared = StudyService(db).get_shared(token)
    return shared


@router.get("/shared/{token}/files/{attachment_id}", tags=["public"])
def shared_attachment(token: str, attachment_id: int, db: DbSession) -> FileResponse:
    service = StudyService(db)
    study, _ = service.get_shared(token)
    attachment = service.get_attachment(attachment_id)
    if attachment.study_id != study.id:
        raise NotFoundError("El archivo no existe")
    return FileResponse(
        service.attachment_path(attachment),
        media_type=attachment.content_type,
        filename=attachment.filename,
    )


@router.get("/patient/{patient_id}", response_model=list[StudyListItem])
def patient_studies(patient_id: int, db: DbSession, current_user: Viewer) -> list[StudyListItem]:
    items = StudyService(db).history_for_patient(patient_id)
    return [StudyListItem.model_validate(item) for item in items]


@router.post("", response_model=StudyRead, status_code=status.HTTP_201_CREATED)
def create_study(payload: StudyCreate, db: DbSession, current_user: Manager) -> StudyRead:
    return StudyRead.model_validate(StudyService(db).create(payload, current_user))


@router.get("/{study_id}", response_model=StudyRead)
def get_study(study_id: int, db: DbSession, current_user: Viewer) -> StudyRead:
    return StudyRead.model_validate(StudyService(db).get(study_id))


@router.put("/{study_id}", response_model=StudyRead)
def update_study(
    study_id: int, payload: StudyUpdate, db: DbSession, current_user: Manager
) -> StudyRead:
    return StudyRead.model_validate(StudyService(db).update(study_id, payload))


@router.post("/{study_id}/result", response_model=StudyRead)
def register_result(
    study_id: int, payload: StudyResultWrite, db: DbSession, current_user: Manager
) -> StudyRead:
    """Registra el informe del estudio y lo marca como completado."""
    return StudyRead.model_validate(StudyService(db).register_result(study_id, payload))


@router.patch("/{study_id}/status", response_model=StudyRead)
def change_study_status(
    study_id: int, payload: StudyStatusChange, db: DbSession, current_user: Manager
) -> StudyRead:
    return StudyRead.model_validate(StudyService(db).change_status(study_id, payload.status))


@router.post(
    "/{study_id}/attachments", response_model=AttachmentRead, status_code=status.HTTP_201_CREATED
)
async def upload_attachment(
    study_id: int,
    db: DbSession,
    current_user: Manager,
    file: Annotated[UploadFile, File(description="PDF o imagen del resultado")],
    description: Annotated[str | None, Form(max_length=255)] = None,
) -> AttachmentRead:
    content = await file.read()
    attachment = StudyService(db).add_attachment(
        study_id,
        content=content,
        filename=file.filename or "resultado",
        content_type=file.content_type,
        description=description,
        actor=current_user,
    )
    return AttachmentRead.model_validate(attachment)


@router.get("/attachments/{attachment_id}/download")
def download_attachment(attachment_id: int, db: DbSession, current_user: Viewer) -> FileResponse:
    service = StudyService(db)
    attachment = service.get_attachment(attachment_id)
    return FileResponse(
        service.attachment_path(attachment),
        media_type=attachment.content_type,
        filename=attachment.filename,
    )


@router.delete("/attachments/{attachment_id}", response_model=OperationResult)
def delete_attachment(
    attachment_id: int, db: DbSession, current_user: Manager
) -> OperationResult:
    StudyService(db).delete_attachment(attachment_id)
    return OperationResult(detail="Archivo eliminado")


@router.post("/{study_id}/share", response_model=ShareLink)
def share_study(study_id: int, db: DbSession, current_user: Manager) -> ShareLink:
    """Genera el enlace temporal y el mensaje de WhatsApp para el paciente."""
    return StudyService(db).create_share_link(study_id)


@router.delete("/{study_id}/share", response_model=StudyRead)
def revoke_share(study_id: int, db: DbSession, current_user: Manager) -> StudyRead:
    return StudyRead.model_validate(StudyService(db).revoke_share_link(study_id))

from datetime import timedelta
from pathlib import Path
from secrets import token_urlsafe

from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.core.datetime import now, to_local
from app.core.messaging import whatsapp_url
from app.models.study import Attachment, ClinicalStudy, StudyStatus
from app.models.user import User
from app.repositories.encounter_repository import EncounterRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.practitioner_repository import PractitionerRepository
from app.repositories.study_repository import AttachmentRepository, StudyRepository
from app.schemas.common import Pagination
from app.schemas.study import (
    ShareLink,
    SharedAttachment,
    SharedStudy,
    StudyCreate,
    StudyResultWrite,
    StudyUpdate,
)
from app.services.exceptions import BusinessRuleError, NotFoundError
from app.services.settings_service import SettingsService

ATTACHMENT_DIR = "studies"
ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/tiff": ".tif",
    "application/dicom": ".dcm",
}

# Transiciones permitidas del estado de un estudio.
ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    StudyStatus.SOLICITADO.value: (
        StudyStatus.EN_PROCESO.value,
        StudyStatus.COMPLETADO.value,
        StudyStatus.ANULADO.value,
    ),
    StudyStatus.EN_PROCESO.value: (
        StudyStatus.COMPLETADO.value,
        StudyStatus.ANULADO.value,
    ),
    StudyStatus.COMPLETADO.value: (StudyStatus.EN_PROCESO.value,),
    StudyStatus.ANULADO.value: (StudyStatus.SOLICITADO.value,),
}


class StudyService:
    """Resultados, Rayos X, archivos y envío al paciente (cláusula 2.4)."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.studies = StudyRepository(db)
        self.attachments = AttachmentRepository(db)
        self.patients = PatientRepository(db)
        self.practitioners = PractitionerRepository(db)
        self.encounters = EncounterRepository(db)

    # --- Consultas ------------------------------------------------------
    def list_studies(self, **filters) -> tuple[list[ClinicalStudy], int]:
        pagination: Pagination = filters.pop("pagination")
        return self.studies.search(pagination=pagination, **filters)

    def get(self, study_id: int) -> ClinicalStudy:
        study = self.studies.get_by_id(study_id)
        if study is None:
            raise NotFoundError("El estudio no existe")
        return study

    def history_for_patient(self, patient_id: int) -> list[ClinicalStudy]:
        return self.studies.list_for_patient(patient_id)

    # --- Registro -------------------------------------------------------
    def create(self, payload: StudyCreate, actor: User) -> ClinicalStudy:
        self._validate_references(payload)
        study = ClinicalStudy(
            patient_id=payload.patient_id,
            encounter_id=payload.encounter_id,
            requested_by_id=payload.requested_by_id,
            service_id=payload.service_id,
            study_type=payload.study_type.value,
            name=payload.name,
            clinical_notes=payload.clinical_notes,
            requested_at=to_local(payload.requested_at) if payload.requested_at else now(),
            status=StudyStatus.SOLICITADO.value,
            created_by_id=actor.id,
        )
        return self.studies.add(study)

    def update(self, study_id: int, payload: StudyUpdate) -> ClinicalStudy:
        study = self.get(study_id)
        self._ensure_open(study)
        self._validate_references(payload)

        study.patient_id = payload.patient_id
        study.encounter_id = payload.encounter_id
        study.requested_by_id = payload.requested_by_id
        study.service_id = payload.service_id
        study.study_type = payload.study_type.value
        study.name = payload.name
        study.clinical_notes = payload.clinical_notes
        return self.studies.save(study)

    def register_result(self, study_id: int, payload: StudyResultWrite) -> ClinicalStudy:
        study = self.get(study_id)
        if study.status == StudyStatus.ANULADO.value:
            raise BusinessRuleError("El estudio está anulado")

        study.result_summary = payload.result_summary
        study.report = payload.report
        study.performed_by = payload.performed_by
        study.performed_at = (
            to_local(payload.performed_at) if payload.performed_at else study.performed_at or now()
        )
        if payload.complete:
            if not study.report and not study.result_summary and not study.attachments:
                raise BusinessRuleError(
                    "Registre el informe, un resumen o adjunte el archivo del resultado"
                )
            study.status = StudyStatus.COMPLETADO.value
        elif study.status == StudyStatus.SOLICITADO.value:
            study.status = StudyStatus.EN_PROCESO.value
        return self.studies.save(study)

    def change_status(self, study_id: int, status: StudyStatus) -> ClinicalStudy:
        study = self.get(study_id)
        target = status.value
        if target == study.status:
            return study
        if target not in ALLOWED_TRANSITIONS.get(study.status, ()):
            raise BusinessRuleError(
                f"No es posible pasar del estado {study.status_label} al solicitado"
            )
        study.status = target
        return self.studies.save(study)

    # --- Archivos -------------------------------------------------------
    def add_attachment(
        self,
        study_id: int,
        *,
        content: bytes,
        filename: str,
        content_type: str | None,
        description: str | None,
        actor: User,
    ) -> Attachment:
        study = self.get(study_id)
        extension = self._validate_file(content, content_type)

        directory = app_settings.storage_path / ATTACHMENT_DIR / str(study.id)
        directory.mkdir(parents=True, exist_ok=True)
        stored_name = f"{token_urlsafe(12)}{extension}"
        (directory / stored_name).write_bytes(content)

        attachment = Attachment(
            patient_id=study.patient_id,
            study_id=study.id,
            encounter_id=study.encounter_id,
            filename=Path(filename).name[:200],
            stored_path=f"{ATTACHMENT_DIR}/{study.id}/{stored_name}",
            content_type=(content_type or "application/octet-stream").lower(),
            size_bytes=len(content),
            description=description,
            uploaded_by_id=actor.id,
        )
        return self.attachments.add(attachment)

    def get_attachment(self, attachment_id: int) -> Attachment:
        attachment = self.attachments.get_by_id(attachment_id)
        if attachment is None:
            raise NotFoundError("El archivo no existe")
        return attachment

    def attachment_path(self, attachment: Attachment) -> Path:
        path = app_settings.storage_path / attachment.stored_path
        if not path.is_file():
            raise NotFoundError("El archivo ya no se encuentra disponible")
        return path

    def delete_attachment(self, attachment_id: int) -> None:
        attachment = self.get_attachment(attachment_id)
        (app_settings.storage_path / attachment.stored_path).unlink(missing_ok=True)
        self.attachments.delete(attachment)

    # --- Envío al paciente ----------------------------------------------
    def create_share_link(self, study_id: int) -> ShareLink:
        """Genera el enlace temporal del resultado y el mensaje de WhatsApp."""
        study = self.get(study_id)
        if not study.is_completed:
            raise BusinessRuleError("Solo se comparten estudios completados")
        if not study.has_result:
            raise BusinessRuleError("El estudio aún no tiene resultado registrado")

        moment = now()
        study.share_token = token_urlsafe(24)
        study.share_expires_at = moment + timedelta(hours=app_settings.SHARE_LINK_HOURS)
        study.shared_at = moment
        self.studies.save(study)

        clinic = SettingsService(self.db).get()
        url = f"{app_settings.PUBLIC_APP_URL.rstrip('/')}/resultados/{study.share_token}"
        message = (
            f"Hola {study.patient.display_name}, {clinic.name} le comparte el resultado de "
            f"«{study.name}». Puede consultarlo en el siguiente enlace: {url} "
            f"(vigente por {app_settings.SHARE_LINK_HOURS} horas)."
        )
        phone = study.patient.whatsapp or study.patient.phone

        return ShareLink(
            study_id=study.id,
            url=url,
            whatsapp_url=whatsapp_url(phone, message),
            message=message,
            expires_at=study.share_expires_at,
        )

    def revoke_share_link(self, study_id: int) -> ClinicalStudy:
        study = self.get(study_id)
        study.share_token = None
        study.share_expires_at = None
        return self.studies.save(study)

    def get_shared(self, token: str) -> tuple[ClinicalStudy, SharedStudy]:
        study = self.studies.get_by_token(token)
        if study is None or study.share_expires_at is None:
            raise NotFoundError("El enlace no es válido")
        if to_local(study.share_expires_at) < now():
            raise BusinessRuleError("El enlace ha vencido. Solicite uno nuevo al policlínico")

        clinic = SettingsService(self.db).get()
        base = f"{app_settings.API_V1_PREFIX}/studies/shared/{token}/files"
        shared = SharedStudy(
            clinic_name=clinic.name,
            clinic_logo_url=clinic.logo_url,
            patient_name=study.patient.display_name,
            study_name=study.name,
            type_label=study.type_label,
            performed_at=study.performed_at,
            result_summary=study.result_summary,
            report=study.report,
            performed_by=study.performed_by,
            attachments=[
                SharedAttachment(
                    id=item.id,
                    filename=item.filename,
                    content_type=item.content_type,
                    size_label=item.size_label,
                    is_image=item.is_image,
                    url=f"{base}/{item.id}",
                )
                for item in study.attachments
            ],
            expires_at=study.share_expires_at,
        )
        return study, shared

    # --- Apoyo ----------------------------------------------------------
    @staticmethod
    def _validate_file(content: bytes, content_type: str | None) -> str:
        extension = ALLOWED_CONTENT_TYPES.get((content_type or "").lower())
        if extension is None:
            raise BusinessRuleError("Formato no permitido. Use PDF, JPG, PNG, WEBP o TIFF")
        if not content:
            raise BusinessRuleError("El archivo está vacío")
        if len(content) > app_settings.MAX_ATTACHMENT_BYTES:
            limit_mb = app_settings.MAX_ATTACHMENT_BYTES // (1024 * 1024)
            raise BusinessRuleError(f"El archivo no debe superar {limit_mb} MB")
        return extension

    @staticmethod
    def _ensure_open(study: ClinicalStudy) -> None:
        if study.status == StudyStatus.ANULADO.value:
            raise BusinessRuleError("El estudio está anulado y no admite cambios")

    def _validate_references(self, payload: StudyCreate | StudyUpdate) -> None:
        if self.patients.get_by_id(payload.patient_id) is None:
            raise BusinessRuleError("El paciente indicado no existe")
        if (
            payload.requested_by_id is not None
            and self.practitioners.get_by_id(payload.requested_by_id) is None
        ):
            raise BusinessRuleError("El profesional solicitante no existe")
        if (
            payload.encounter_id is not None
            and self.encounters.get_by_id(payload.encounter_id) is None
        ):
            raise BusinessRuleError("La atención indicada no existe")

from datetime import date

from sqlalchemy import Select, func, or_, select

from app.core.datetime import end_of_day, start_of_day
from app.models.document import ClinicalDocument, DocumentStatus, DocumentTemplate
from app.models.patient import Patient
from app.repositories.base import BaseRepository
from app.schemas.common import Pagination


class DocumentTemplateRepository(BaseRepository[DocumentTemplate]):
    model = DocumentTemplate

    def get_active(self, code: str) -> DocumentTemplate | None:
        """Versión vigente de una plantilla; es la que se usa al emitir."""
        stmt = (
            select(DocumentTemplate)
            .where(DocumentTemplate.code == code, DocumentTemplate.is_active.is_(True))
            .order_by(DocumentTemplate.version.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_version(self, code: str, version: int) -> DocumentTemplate | None:
        stmt = select(DocumentTemplate).where(
            DocumentTemplate.code == code, DocumentTemplate.version == version
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_active(self, family: str | None = None) -> list[DocumentTemplate]:
        stmt = select(DocumentTemplate).where(DocumentTemplate.is_active.is_(True))
        if family:
            stmt = stmt.where(DocumentTemplate.family == family)
        stmt = stmt.order_by(DocumentTemplate.family, DocumentTemplate.title)
        return list(self.db.execute(stmt).scalars().all())

    def versions_of(self, code: str) -> list[DocumentTemplate]:
        stmt = (
            select(DocumentTemplate)
            .where(DocumentTemplate.code == code)
            .order_by(DocumentTemplate.version.desc())
        )
        return list(self.db.execute(stmt).scalars().all())


class ClinicalDocumentRepository(BaseRepository[ClinicalDocument]):
    model = ClinicalDocument

    def search(
        self,
        *,
        term: str | None = None,
        patient_id: int | None = None,
        family: str | None = None,
        status: str | None = None,
        template_code: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        pagination: Pagination,
    ) -> tuple[list[ClinicalDocument], int]:
        stmt = self._apply_filters(
            select(ClinicalDocument).join(ClinicalDocument.patient),
            term=term,
            patient_id=patient_id,
            family=family,
            status=status,
            template_code=template_code,
            date_from=date_from,
            date_to=date_to,
        ).order_by(ClinicalDocument.created_at.desc(), ClinicalDocument.id.desc())
        return self.paginate(stmt, pagination)

    def list_for_patient(self, patient_id: int, limit: int = 100) -> list[ClinicalDocument]:
        stmt = (
            select(ClinicalDocument)
            .where(ClinicalDocument.patient_id == patient_id)
            .order_by(ClinicalDocument.created_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def list_for_study(self, study_id: int) -> list[ClinicalDocument]:
        stmt = (
            select(ClinicalDocument)
            .where(ClinicalDocument.study_id == study_id)
            .order_by(ClinicalDocument.created_at.desc())
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def count_drafts(self) -> int:
        stmt = select(func.count(ClinicalDocument.id)).where(
            ClinicalDocument.status == DocumentStatus.BORRADOR.value
        )
        return self.db.execute(stmt).scalar_one()

    @staticmethod
    def _apply_filters(
        stmt: Select[tuple[ClinicalDocument]],
        *,
        term: str | None,
        patient_id: int | None,
        family: str | None,
        status: str | None,
        template_code: str | None,
        date_from: date | None,
        date_to: date | None,
    ) -> Select[tuple[ClinicalDocument]]:
        if term:
            pattern = f"%{term.strip().lower()}%"
            full_name = func.lower(
                Patient.last_name_paternal
                + " "
                + func.coalesce(Patient.last_name_maternal, "")
                + " "
                + Patient.first_name
            )
            stmt = stmt.where(
                or_(
                    full_name.like(pattern),
                    func.lower(Patient.document_number).like(pattern),
                    func.lower(ClinicalDocument.title).like(pattern),
                )
            )
        if patient_id is not None:
            stmt = stmt.where(ClinicalDocument.patient_id == patient_id)
        if family:
            stmt = stmt.where(ClinicalDocument.family == family)
        if status:
            stmt = stmt.where(ClinicalDocument.status == status)
        if template_code:
            stmt = stmt.where(ClinicalDocument.template_code == template_code)
        if date_from is not None:
            stmt = stmt.where(ClinicalDocument.created_at >= start_of_day(date_from))
        if date_to is not None:
            stmt = stmt.where(ClinicalDocument.created_at <= end_of_day(date_to))
        return stmt

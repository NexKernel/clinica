from datetime import date

from sqlalchemy import Select, func, or_, select

from app.core.datetime import end_of_day, start_of_day
from app.models.patient import Patient
from app.models.study import Attachment, ClinicalStudy, StudyStatus
from app.repositories.base import BaseRepository
from app.schemas.common import Pagination


class StudyRepository(BaseRepository[ClinicalStudy]):
    model = ClinicalStudy

    def get_by_token(self, token: str) -> ClinicalStudy | None:
        stmt = select(ClinicalStudy).where(ClinicalStudy.share_token == token)
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def search(
        self,
        *,
        term: str | None = None,
        patient_id: int | None = None,
        study_type: str | None = None,
        status: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        pagination: Pagination,
    ) -> tuple[list[ClinicalStudy], int]:
        stmt = self._apply_filters(
            select(ClinicalStudy).join(ClinicalStudy.patient),
            term=term,
            patient_id=patient_id,
            study_type=study_type,
            status=status,
            date_from=date_from,
            date_to=date_to,
        ).order_by(ClinicalStudy.requested_at.desc(), ClinicalStudy.id.desc())
        return self.paginate(stmt, pagination)

    def list_for_patient(self, patient_id: int, limit: int = 100) -> list[ClinicalStudy]:
        stmt = (
            select(ClinicalStudy)
            .where(ClinicalStudy.patient_id == patient_id)
            .order_by(ClinicalStudy.requested_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(stmt).unique().scalars().all())

    def count_pending(self) -> int:
        stmt = select(func.count(ClinicalStudy.id)).where(
            ClinicalStudy.status.in_(
                (StudyStatus.SOLICITADO.value, StudyStatus.EN_PROCESO.value)
            )
        )
        return self.db.execute(stmt).scalar_one()

    @staticmethod
    def _apply_filters(
        stmt: Select[tuple[ClinicalStudy]],
        *,
        term: str | None,
        patient_id: int | None,
        study_type: str | None,
        status: str | None,
        date_from: date | None,
        date_to: date | None,
    ) -> Select[tuple[ClinicalStudy]]:
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
                    func.lower(ClinicalStudy.name).like(pattern),
                )
            )
        if patient_id is not None:
            stmt = stmt.where(ClinicalStudy.patient_id == patient_id)
        if study_type:
            stmt = stmt.where(ClinicalStudy.study_type == study_type)
        if status:
            stmt = stmt.where(ClinicalStudy.status == status)
        if date_from is not None:
            stmt = stmt.where(ClinicalStudy.requested_at >= start_of_day(date_from))
        if date_to is not None:
            stmt = stmt.where(ClinicalStudy.requested_at <= end_of_day(date_to))
        return stmt


class AttachmentRepository(BaseRepository[Attachment]):
    model = Attachment

    def list_for_encounter(self, encounter_id: int) -> list[Attachment]:
        stmt = (
            select(Attachment)
            .where(Attachment.encounter_id == encounter_id)
            .order_by(Attachment.id)
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_for_patient(self, patient_id: int) -> list[Attachment]:
        stmt = (
            select(Attachment)
            .where(Attachment.patient_id == patient_id)
            .order_by(Attachment.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

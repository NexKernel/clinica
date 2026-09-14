"""Documentos clínicos: informes, fichas, consentimientos y actas.

Implementa la opción B del análisis de `formatos_clinica`: el formato en papel
se transcribe una sola vez a HTML y el sistema lo combina con los datos que ya
administra (establecimiento, paciente, profesional, atención). El resultado se
imprime desde el navegador y, al emitirse, queda congelado como constancia.
"""

import base64
from datetime import datetime
from mimetypes import guess_type
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings as app_settings
from app.core.datetime import now, to_local
from app.core.templating import MONTHS, field_keys, render, to_plain_text, wrap_document
from app.models.document import (
    ClinicalDocument,
    DocumentFamily,
    DocumentStatus,
    DocumentTemplate,
)
from app.models.encounter import Prescription
from app.models.settings import ClinicSettings
from app.models.study import StudyStatus
from app.models.user import User
from app.repositories.document_repository import (
    ClinicalDocumentRepository,
    DocumentTemplateRepository,
)
from app.repositories.encounter_repository import EncounterRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.practitioner_repository import PractitionerRepository
from app.repositories.study_repository import StudyRepository
from app.schemas.common import Pagination
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.services.exceptions import BusinessRuleError, NotFoundError
from app.services.settings_service import SettingsService

# Un logo más pesado que esto no se incrusta: el documento quedaría inmanejable.
MAX_EMBEDDED_LOGO_BYTES = 512 * 1024


class DocumentService:
    """Catálogo de plantillas y ciclo de vida de los documentos emitidos."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.templates = DocumentTemplateRepository(db)
        self.documents = ClinicalDocumentRepository(db)
        self.patients = PatientRepository(db)
        self.practitioners = PractitionerRepository(db)
        self.encounters = EncounterRepository(db)
        self.studies = StudyRepository(db)
        self._clinic: ClinicSettings | None = None

    def _settings(self) -> ClinicSettings:
        """Configuración del establecimiento, leída una sola vez por operación."""
        if self._clinic is None:
            self._clinic = SettingsService(self.db).get()
        return self._clinic

    # --- Catálogo -------------------------------------------------------
    def list_templates(self, family: str | None = None) -> list[DocumentTemplate]:
        return self.templates.list_active(family)

    def get_template(self, code: str) -> DocumentTemplate:
        template = self.templates.get_active(code)
        if template is None:
            raise NotFoundError("La plantilla no existe o fue retirada del catálogo")
        return template

    # --- Consultas ------------------------------------------------------
    def list_documents(self, **filters: Any) -> tuple[list[ClinicalDocument], int]:
        pagination: Pagination = filters.pop("pagination")
        return self.documents.search(pagination=pagination, **filters)

    def get(self, document_id: int) -> ClinicalDocument:
        document = self.documents.get_by_id(document_id)
        if document is None:
            raise NotFoundError("El documento no existe")
        return document

    def history_for_patient(self, patient_id: int) -> list[ClinicalDocument]:
        return self.documents.list_for_patient(patient_id)

    def fields_of(self, document: ClinicalDocument) -> list[dict[str, Any]]:
        """Definición de campos con la que se llenó el documento.

        Se lee de la versión registrada, no de la vigente: un documento emitido
        con la versión 1 debe seguir mostrándose con los campos de esa versión.
        """
        template = self.templates.get_version(
            document.template_code, document.template_version
        )
        return list((template or document.template).fields or [])

    # --- Emisión --------------------------------------------------------
    def create(self, payload: DocumentCreate, actor: User) -> ClinicalDocument:
        template = self.get_template(payload.template_code)
        self._validate_references(payload)

        document = ClinicalDocument(
            patient_id=payload.patient_id,
            encounter_id=payload.encounter_id,
            study_id=payload.study_id,
            practitioner_id=payload.practitioner_id,
            template_id=template.id,
            template_code=template.code,
            template_version=template.version,
            family=template.family,
            title=template.title,
            status=DocumentStatus.BORRADOR.value,
            # Los valores sugeridos por la plantilla se aplican solo donde el
            # usuario no escribió nada: el hallazgo normal del formato impreso.
            data={**template.defaults, **payload.data},
            created_by_id=actor.id,
        )
        return self.documents.add(document)

    def update(self, document_id: int, payload: DocumentUpdate) -> ClinicalDocument:
        document = self.get(document_id)
        self._ensure_draft(document)
        self._validate_references(payload)

        document.patient_id = payload.patient_id
        document.encounter_id = payload.encounter_id
        document.study_id = payload.study_id
        document.practitioner_id = payload.practitioner_id
        document.data = dict(payload.data)
        return self.documents.save(document)

    def issue(self, document_id: int, actor: User) -> ClinicalDocument:
        """Congela el documento: lo que se imprime desde aquí ya no cambia."""
        document = self.get(document_id)
        if document.status == DocumentStatus.ANULADO.value:
            raise BusinessRuleError("El documento está anulado")
        if document.is_issued:
            return document

        self._require_fields(document)
        document.content = self.render(document)
        document.status = DocumentStatus.EMITIDO.value
        document.issued_at = now()
        document.issued_by_id = actor.id
        self.documents.save(document)

        self._push_to_study(document)
        return document

    def void(self, document_id: int, reason: str) -> ClinicalDocument:
        document = self.get(document_id)
        if document.status == DocumentStatus.ANULADO.value:
            return document
        document.status = DocumentStatus.ANULADO.value
        document.voided_at = now()
        document.void_reason = reason
        return self.documents.save(document)

    def delete(self, document_id: int) -> None:
        document = self.get(document_id)
        self._ensure_draft(document)
        self.documents.delete(document)

    # --- Composición ----------------------------------------------------
    def preview(self, document: ClinicalDocument) -> str:
        """Hoja del documento: la congelada si fue emitido, o una en vivo."""
        return document.content or self.render(document)

    def render(self, document: ClinicalDocument) -> str:
        template = (
            self.templates.get_version(document.template_code, document.template_version)
            or document.template
        )
        context = self.build_context(document)
        return wrap_document(
            title=template.title,
            body_html=render(template.body, context),
            context=context,
            logo_src=_embedded_logo(self._settings().logo_path),
        )

    def build_context(self, document: ClinicalDocument) -> dict[str, dict[str, Any]]:
        """Contexto de fusión: el único lugar del que salen los datos impresos.

        Aquí mueren los datos quemados de los formatos en Word (nombre del
        médico, CMP, dirección, teléfonos y fechas fijas): todos provienen de la
        configuración del establecimiento y de las fichas ya registradas.
        """
        clinic = self._settings()
        patient = document.patient
        practitioner = document.practitioner or (
            document.encounter.practitioner if document.encounter else None
        )
        encounter = document.encounter
        study = document.study
        moment = to_local(document.issued_at) if document.issued_at else now()

        return {
            "clinica": {
                "nombre": clinic.name,
                "nombre_corto": clinic.short_name,
                "nombre_legal": clinic.legal_name,
                "ruc": clinic.tax_id,
                "direccion": clinic.address,
                "distrito": clinic.district,
                "provincia": clinic.province,
                "departamento": clinic.department,
                "ubicacion": clinic.location,
                "telefono": clinic.phone,
                "whatsapp": clinic.whatsapp,
                "correo": clinic.email,
                "sitio_web": clinic.website,
                "codigo_renipress": clinic.health_facility_code,
                "categoria": clinic.category,
                "director_medico": clinic.medical_director,
                "pie": clinic.document_footer,
            },
            "paciente": {
                "nombre_completo": patient.full_name,
                "nombres": patient.first_name,
                "apellidos": " ".join(
                    part
                    for part in (patient.last_name_paternal, patient.last_name_maternal)
                    if part
                ),
                "historia": patient.history_number,
                "tipo_documento": patient.document_type,
                "documento": patient.document_number,
                "edad": f"{patient.age} años" if patient.age is not None else None,
                "sexo": patient.sex_label,
                "fecha_nacimiento": self._date_text(patient.birth_date),
                "direccion": patient.address,
                "telefono": patient.phone,
                "whatsapp": patient.whatsapp,
                "correo": patient.email,
                "seguro": patient.insurance,
                "grupo_sanguineo": patient.blood_type,
                "alergias": patient.allergies,
            },
            "profesional": {
                "nombre": practitioner.full_name if practitioner else None,
                "cmp": practitioner.license_number if practitioner else None,
                "documento": practitioner.document_number if practitioner else None,
                "especialidad": practitioner.specialty_name if practitioner else None,
                "telefono": practitioner.phone if practitioner else None,
            },
            "atencion": {
                "fecha": self._date_text(encounter.started_at) if encounter else None,
                "hora": self._time_text(encounter.started_at) if encounter else None,
                "motivo": encounter.chief_complaint if encounter else None,
                "diagnostico": encounter.main_diagnosis if encounter else None,
                # Listas ya compuestas: la plantilla las pinta con el filtro
                # `|lista` y el motor escapa cada línea por separado.
                "diagnosticos": [item.summary for item in encounter.diagnoses]
                if encounter
                else [],
                "medicamentos": [
                    _prescription_line(item) for item in encounter.prescriptions
                ]
                if encounter
                else [],
                "indicaciones": encounter.indications if encounter else None,
                "plan": encounter.treatment_plan if encounter else None,
                "presion_arterial": encounter.blood_pressure if encounter else None,
                "frecuencia_cardiaca": encounter.heart_rate if encounter else None,
                "frecuencia_respiratoria": encounter.respiratory_rate if encounter else None,
                "temperatura": encounter.temperature if encounter else None,
                "peso": encounter.weight_kg if encounter else None,
                "talla": encounter.height_cm if encounter else None,
            },
            "estudio": {
                "nombre": study.name if study else None,
                "tipo": study.type_label if study else None,
                "fecha": self._date_text(study.performed_at or study.requested_at)
                if study
                else None,
                "solicitado_por": study.requested_by_name if study else None,
            },
            "fecha": {
                "hoy": self._date_text(moment),
                "dia": f"{moment.day:02d}",
                "mes": MONTHS[moment.month - 1],
                "anio": str(moment.year),
                "hora": self._time_text(moment),
                "larga": f"{moment.day} de {MONTHS[moment.month - 1]} de {moment.year}",
                "lugar_larga": self._place_and_date(clinic.district, moment),
            },
            "documento": {
                "numero": document.number,
                "titulo": document.title,
                "version": f"v{document.template_version}",
            },
            "campo": dict(document.data or {}),
        }

    # --- Integración con estudios ---------------------------------------
    def _push_to_study(self, document: ClinicalDocument) -> None:
        """Vuelca el informe emitido al estudio para poder enviarlo al paciente.

        Reutiliza el circuito de la cláusula 2.4 que ya existe (informe, enlace
        temporal y mensaje de WhatsApp) en lugar de abrir uno paralelo.
        """
        if document.family != DocumentFamily.INFORME.value or document.study_id is None:
            return
        study = self.studies.get_by_id(document.study_id)
        if study is None or study.status == StudyStatus.ANULADO.value:
            return

        study.report = to_plain_text(document.content or "")
        conclusion = str(document.data.get("conclusion") or "").strip()
        if conclusion:
            study.result_summary = conclusion[:255]
        study.performed_at = study.performed_at or document.issued_at
        if document.practitioner_name:
            study.performed_by = document.practitioner_name
        study.status = StudyStatus.COMPLETADO.value
        self.studies.save(study)

    # --- Apoyo ----------------------------------------------------------
    def _require_fields(self, document: ClinicalDocument) -> None:
        missing = [
            field["label"]
            for field in self.fields_of(document)
            if field.get("required") and not str(document.data.get(field["key"]) or "").strip()
        ]
        if missing:
            raise BusinessRuleError(f"Complete antes de emitir: {', '.join(missing)}")

    @staticmethod
    def _ensure_draft(document: ClinicalDocument) -> None:
        if not document.is_draft:
            raise BusinessRuleError(
                "El documento ya fue emitido. Anúlelo y emita uno nuevo para corregirlo"
            )

    def _validate_references(self, payload: DocumentCreate | DocumentUpdate) -> None:
        if self.patients.get_by_id(payload.patient_id) is None:
            raise BusinessRuleError("El paciente indicado no existe")
        if (
            payload.practitioner_id is not None
            and self.practitioners.get_by_id(payload.practitioner_id) is None
        ):
            raise BusinessRuleError("El profesional indicado no existe")
        if (
            payload.encounter_id is not None
            and self.encounters.get_by_id(payload.encounter_id) is None
        ):
            raise BusinessRuleError("La atención indicada no existe")
        if payload.study_id is not None and self.studies.get_by_id(payload.study_id) is None:
            raise BusinessRuleError("El estudio indicado no existe")

    @staticmethod
    def _date_text(value: Any) -> str | None:
        if value is None:
            return None
        moment = to_local(value) if isinstance(value, datetime) else value
        return f"{moment.day:02d}/{moment.month:02d}/{moment.year}"

    @staticmethod
    def _time_text(value: datetime | None) -> str | None:
        return to_local(value).strftime("%H:%M") if value else None

    @staticmethod
    def _place_and_date(place: str | None, moment: datetime) -> str:
        """«Satipo, 4 de setiembre de 2026», el encabezado de casi todo formato."""
        text = f"{moment.day} de {MONTHS[moment.month - 1]} de {moment.year}"
        return f"{place}, {text}" if place else text

    @staticmethod
    def validate_template(template: DocumentTemplate) -> list[str]:
        """Incoherencias entre el cuerpo de la plantilla y su esquema de campos."""
        declared = {field["key"] for field in (template.fields or [])}
        used = field_keys(template.body)
        problems = [f"campo sin definir: {key}" for key in sorted(used - declared)]
        problems += [f"campo definido pero no usado: {key}" for key in sorted(declared - used)]
        return problems


def _prescription_line(prescription: Prescription) -> str:
    """Una línea de receta: «Paracetamol 500 mg — 1 tableta cada 8 h por 5 días»."""
    parts = [prescription.medication]
    if prescription.schedule_label:
        parts.append(f"— {prescription.schedule_label}")
    if prescription.quantity:
        parts.append(f"(cantidad: {prescription.quantity})")
    if prescription.instructions:
        parts.append(f"· {prescription.instructions}")
    return " ".join(parts)


def _embedded_logo(logo_path: str | None) -> str | None:
    """Logo del policlínico como data URI, o None si no hay o es muy pesado.

    Se incrusta en lugar de enlazarse: un documento emitido es una constancia y
    debe verse igual dentro de un año, aunque cambie el dominio o se reemplace
    el archivo del logotipo.
    """
    if not logo_path:
        return None

    path = app_settings.media_path / logo_path
    if not path.is_file() or path.stat().st_size > MAX_EMBEDDED_LOGO_BYTES:
        return None

    media_type = guess_type(path.name)[0] or "image/png"
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{payload}"

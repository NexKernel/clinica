from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import DbSession, require_manage, require_view
from app.core.permissions import ModuleCode
from app.models import User
from app.schemas.cred import (
    CredCard,
    CredCatalogItem,
    CredEntryCreate,
    CredEntryRead,
    CredEntryWrite,
    CredSheet,
)
from app.services.cred_service import CredService, render_card_sheet
from app.services.patient_service import PatientService

router = APIRouter(prefix="/cred", tags=["cred"])

Viewer = Annotated[User, Depends(require_view(ModuleCode.CRED))]
Manager = Annotated[User, Depends(require_manage(ModuleCode.CRED))]


@router.get("/catalog", response_model=list[CredCatalogItem])
def catalog(db: DbSession, _: Viewer, patient_id: int) -> list[CredCatalogItem]:
    """Prestaciones del calendario, marcando las que este niño ya recibió."""
    return CredService(db).catalog(patient_id)


@router.get("/{patient_id}", response_model=CredCard)
def card(db: DbSession, _: Viewer, patient_id: int) -> CredCard:
    patient = PatientService(db).get(patient_id)
    return CredService(db).card(patient)


@router.get("/{patient_id}/sheet", response_model=CredSheet)
def sheet(db: DbSession, _: Viewer, patient_id: int) -> CredSheet:
    """Hoja del carné, con el mismo membrete que el resto de documentos."""
    from app.core.templating import wrap_document
    from app.services.document_service import DocumentService, _embedded_logo

    patient = PatientService(db).get(patient_id)
    card = CredService(db).card(patient)
    clinic = DocumentService(db)._settings()
    contexto = {"clinica": {"nombre": clinic.name, "nombre_legal": clinic.legal_name,
                            "direccion": clinic.address, "distrito": clinic.district,
                            "telefono": clinic.phone, "ruc": clinic.tax_id,
                            "pie": clinic.document_footer}}
    titulo = "Carné de atención integral de la niña y el niño"
    return CredSheet(
        title=titulo,
        number=patient.history_number,
        html=wrap_document(
            title=titulo,
            body_html=(
                f'<table class="doc-grid">'
                f'<tr><td class="k">Niño o niña</td><td>{patient.full_name}</td>'
                f'<td class="k">Historia</td><td>{patient.history_number}</td></tr>'
                f'<tr><td class="k">Documento</td><td>{patient.document_label}</td>'
                f'<td class="k">Sexo</td><td>{patient.sex_label or ""}</td></tr>'
                f"</table>" + render_card_sheet(card)
            ),
            context=contexto,
            logo_src=_embedded_logo(clinic.logo_path),
        ),
    )


@router.post("", response_model=CredEntryRead, status_code=status.HTTP_201_CREATED)
def create_entry(db: DbSession, actor: Manager, payload: CredEntryCreate) -> CredEntryRead:
    return CredEntryRead.model_validate(CredService(db).create(payload, actor))


@router.put("/{entry_id}", response_model=CredEntryRead)
def update_entry(db: DbSession, _: Manager, entry_id: int, payload: CredEntryWrite) -> CredEntryRead:
    return CredEntryRead.model_validate(CredService(db).update(entry_id, payload))


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(db: DbSession, _: Manager, entry_id: int) -> None:
    CredService(db).delete(entry_id)

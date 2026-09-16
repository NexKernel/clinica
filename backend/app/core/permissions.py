"""Matriz de permisos por módulo (cláusula 2.10 del contrato).

Define, en un solo lugar, qué perfiles pueden consultar y qué perfiles pueden
registrar información en cada módulo. Las rutas la consumen mediante las
dependencias `require_view` / `require_manage` de `app.api.deps`.
"""

from enum import StrEnum

from app.models.role import RoleCode

A = RoleCode.ADMIN
REC = RoleCode.RECEPCION
MED = RoleCode.MEDICO
ENF = RoleCode.ENFERMERIA
CAJ = RoleCode.CAJA
ALM = RoleCode.ALMACEN
LAB = RoleCode.LABORATORIO
OPT = RoleCode.OPTOMETRIA


class ModuleCode(StrEnum):
    PATIENTS = "PATIENTS"
    APPOINTMENTS = "APPOINTMENTS"
    ENCOUNTERS = "ENCOUNTERS"
    MEDICAL_RECORDS = "MEDICAL_RECORDS"
    STUDIES = "STUDIES"
    DOCUMENTS = "DOCUMENTS"
    REMINDERS = "REMINDERS"
    PHARMACY = "PHARMACY"
    PURCHASES = "PURCHASES"
    SALES = "SALES"
    BILLING = "BILLING"
    REPORTS = "REPORTS"
    CATALOG = "CATALOG"
    USERS = "USERS"
    SETTINGS = "SETTINGS"
    AUDIT = "AUDIT"


class ModulePermission:
    """Perfiles con acceso de consulta y de registro sobre un módulo."""

    __slots__ = ("code", "name", "view", "manage")

    def __init__(
        self,
        code: ModuleCode,
        name: str,
        view: tuple[RoleCode, ...],
        manage: tuple[RoleCode, ...],
    ) -> None:
        self.code = code
        self.name = name
        self.view = view
        self.manage = manage


def _module(
    code: ModuleCode,
    name: str,
    view: tuple[RoleCode, ...],
    manage: tuple[RoleCode, ...],
    *,
    admin_manages: bool = True,
) -> ModulePermission:
    """Declara un módulo. El administrador siempre conserva la consulta.

    Con `admin_manages=False` la conserva *solo* como consulta: es el caso de la
    historia clínica, donde lo escrito responde a quien atendió al paciente y
    firma el acto médico. Que el administrador pueda leerla para auditar no lo
    habilita a modificarla; un registro clínico editable por quien no atendió
    pierde su valor legal.
    """
    return ModulePermission(code, name, (A, *view), (A, *manage) if admin_manages else manage)


PERMISSION_MATRIX: dict[ModuleCode, ModulePermission] = {
    module.code: module
    for module in (
        _module(
            ModuleCode.PATIENTS,
            "Pacientes",
            view=(REC, MED, ENF, CAJ, LAB, OPT),
            manage=(REC, MED, ENF),
        ),
        _module(
            ModuleCode.APPOINTMENTS,
            "Agenda de citas",
            view=(REC, MED, ENF, CAJ, LAB, OPT),
            manage=(REC, MED, ENF),
        ),
        # Solo escribe la historia quien atiende: el administrador la consulta
        # para auditar, pero no la edita.
        _module(
            ModuleCode.ENCOUNTERS,
            "Atenciones médicas",
            view=(MED, ENF, OPT),
            manage=(MED, ENF, OPT),
            admin_manages=False,
        ),
        _module(
            ModuleCode.MEDICAL_RECORDS,
            "Historias clínicas",
            view=(MED, ENF, OPT),
            manage=(MED,),
            admin_manages=False,
        ),
        _module(
            ModuleCode.STUDIES,
            "Resultados y Rayos X",
            view=(REC, MED, ENF, LAB, OPT),
            manage=(MED, ENF, LAB, OPT),
        ),
        # Recepción emite y hace firmar los consentimientos y declaraciones;
        # los informes y fichas los llena el personal asistencial.
        _module(
            ModuleCode.DOCUMENTS,
            "Documentos y formatos",
            view=(REC, MED, ENF, LAB, OPT),
            manage=(REC, MED, ENF, LAB, OPT),
        ),
        _module(
            ModuleCode.REMINDERS,
            "Recordatorios",
            view=(REC, MED, ENF),
            manage=(REC, MED, ENF),
        ),
        _module(ModuleCode.PHARMACY, "Farmacia y almacén", view=(ALM, CAJ, MED), manage=(ALM,)),
        _module(ModuleCode.PURCHASES, "Compras", view=(ALM, CAJ), manage=(ALM,)),
        _module(ModuleCode.SALES, "Notas de venta", view=(CAJ, ALM, REC), manage=(CAJ, ALM)),
        _module(ModuleCode.BILLING, "Facturación", view=(CAJ,), manage=(CAJ,)),
        _module(ModuleCode.REPORTS, "Reportes", view=(CAJ,), manage=()),
        _module(
            ModuleCode.CATALOG,
            "Catálogos y tarifario",
            view=(REC, MED, ENF, CAJ, ALM, LAB, OPT),
            manage=(),
        ),
        _module(ModuleCode.USERS, "Usuarios y perfiles", view=(), manage=()),
        _module(ModuleCode.SETTINGS, "Configuración", view=(), manage=()),
        _module(ModuleCode.AUDIT, "Auditoría", view=(), manage=()),
    )
}


def can_view(role_code: str, module: ModuleCode) -> bool:
    permission = PERMISSION_MATRIX[module]
    return role_code in {role.value for role in permission.view}


def can_manage(role_code: str, module: ModuleCode) -> bool:
    permission = PERMISSION_MATRIX[module]
    return role_code in {role.value for role in permission.manage}


def modules_for_role(role_code: str) -> list[dict[str, object]]:
    """Matriz de acceso del perfil indicado, para la vista de administración."""
    return [
        {
            "code": permission.code.value,
            "name": permission.name,
            "can_view": can_view(role_code, permission.code),
            "can_manage": can_manage(role_code, permission.code),
        }
        for permission in PERMISSION_MATRIX.values()
    ]

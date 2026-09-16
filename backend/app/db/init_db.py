import logging
from collections.abc import Callable

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.db.base import Base
from app.db.document_seeds import seed_document_templates
from app.db.migrations import apply_schema_updates
from app.db.seeds import seed_catalog
from app.db.session import SessionLocal, engine
from app.models import ROLE_CATALOG, Role, User
from app.repositories.user_repository import RoleRepository, UserRepository
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)


def _seed_roles(db: Session) -> None:
    repo = RoleRepository(db)
    created = False
    for code, (name, description) in ROLE_CATALOG.items():
        existing = repo.get_by_code(code.value)
        if existing is None:
            db.add(Role(code=code.value, name=name, description=description))
            created = True
        elif existing.name != name or existing.description != description:
            existing.name, existing.description = name, description
            created = True
    if created:
        db.commit()


def _admin_account(users: UserRepository) -> User | None:
    """Localiza la cuenta inicial por usuario o por correo.

    Buscar también por correo evita que, al renombrar FIRST_ADMIN_USERNAME, se
    intente crear un segundo usuario con el mismo email (violaría el unique y
    abortaría todo el init_db).
    """
    return users.get_by_identifier(settings.FIRST_ADMIN_USERNAME) or users.get_by_identifier(
        settings.FIRST_ADMIN_EMAIL
    )


def _from_env(field: str) -> bool:
    """True si el valor lo puso el entorno (o el .env) y no el default de Settings."""
    return field in settings.model_fields_set


def _seed_admin(db: Session) -> None:
    users = UserRepository(db)
    admin = _admin_account(users)
    if admin is None:
        _create_admin(db, users)
    else:
        _sync_admin(users, admin)


def _create_admin(db: Session, users: UserRepository) -> None:
    admin_role = RoleRepository(db).get_by_code("ADMIN")
    if admin_role is None:
        return
    users.create(
        User(
            username=settings.FIRST_ADMIN_USERNAME,
            email=settings.FIRST_ADMIN_EMAIL,
            password_hash=hash_password(settings.FIRST_ADMIN_PASSWORD),
            full_name=settings.FIRST_ADMIN_FULL_NAME,
            role_id=admin_role.id,
            is_active=True,
            is_system=True,
        )
    )
    logger.info("Usuario administrador inicial creado: %s", settings.FIRST_ADMIN_USERNAME)


def _sync_admin(users: UserRepository, admin: User) -> None:
    """Realinea la cuenta de soporte con las variables FIRST_ADMIN_*.

    Antes el sembrado salía en cuanto la cuenta existía, así que cambiar la
    contraseña en el entorno tras el primer despliegue no tenía ningún efecto:
    seguía valiendo el hash del primer arranque. El entorno manda, de modo que
    una contraseña cambiada desde la aplicación se revierte al reiniciar si no
    se actualiza también FIRST_ADMIN_PASSWORD.
    """
    changes: list[str] = []

    if _from_env("FIRST_ADMIN_USERNAME") and admin.username != settings.FIRST_ADMIN_USERNAME:
        if users.username_taken(settings.FIRST_ADMIN_USERNAME, exclude_id=admin.id):
            logger.warning(
                "FIRST_ADMIN_USERNAME (%s) ya lo usa otra cuenta; se conserva %s.",
                settings.FIRST_ADMIN_USERNAME,
                admin.username,
            )
        else:
            admin.username = settings.FIRST_ADMIN_USERNAME
            changes.append("usuario")

    if _from_env("FIRST_ADMIN_EMAIL") and admin.email.lower() != settings.FIRST_ADMIN_EMAIL.lower():
        if users.email_taken(settings.FIRST_ADMIN_EMAIL, exclude_id=admin.id):
            logger.warning(
                "FIRST_ADMIN_EMAIL (%s) ya lo usa otra cuenta; se conserva %s.",
                settings.FIRST_ADMIN_EMAIL,
                admin.email,
            )
        else:
            admin.email = settings.FIRST_ADMIN_EMAIL
            changes.append("correo")

    if _from_env("FIRST_ADMIN_FULL_NAME") and admin.full_name != settings.FIRST_ADMIN_FULL_NAME:
        admin.full_name = settings.FIRST_ADMIN_FULL_NAME
        changes.append("nombre")

    if _from_env("FIRST_ADMIN_PASSWORD") and not verify_password(
        settings.FIRST_ADMIN_PASSWORD, admin.password_hash
    ):
        admin.password_hash = hash_password(settings.FIRST_ADMIN_PASSWORD)
        changes.append("contraseña")

    if not admin.is_active:
        admin.is_active = True
        changes.append("reactivación")

    if not admin.is_system:
        # Marca la cuenta creada antes de que existiera la bandera.
        admin.is_system = True
        changes.append("cuenta de soporte")

    if changes:
        users.save(admin)
        logger.info("Cuenta %s sincronizada con el entorno: %s", admin.username, ", ".join(changes))


def _run_step(db: Session, label: str, step: Callable[[Session], object]) -> bool:
    """Ejecuta un paso del sembrado sin dejar que se lleve por delante a los siguientes.

    main.py atrapa lo que salga de init_db(), así que sin este aislamiento un
    fallo temprano dejaba la aplicación arrancada y a medio sembrar, en
    silencio. Se registra la traza y se sigue: es preferible un módulo incompleto
    y anunciado a una instalación muda.
    """
    try:
        step(db)
    except Exception:
        db.rollback()
        logger.exception("Falló el sembrado de %s", label)
        return False
    return True


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    apply_schema_updates(engine)
    with SessionLocal() as db:
        steps: tuple[tuple[str, Callable[[Session], object]], ...] = (
            ("roles", _seed_roles),
            ("administrador", _seed_admin),
            ("catálogo", seed_catalog),
            ("plantillas de documentos", seed_document_templates),
            ("configuración de la clínica", lambda session: SettingsService(session).get()),
        )
        failed = [label for label, step in steps if not _run_step(db, label, step)]

    if failed:
        logger.error("Sembrado incompleto: %s", ", ".join(failed))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()

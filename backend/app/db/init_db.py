import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
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


def _seed_admin(db: Session) -> None:
    users = UserRepository(db)
    if users.get_by_identifier(settings.FIRST_ADMIN_USERNAME) is not None:
        return
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
        )
    )
    logger.info("Usuario administrador inicial creado: %s", settings.FIRST_ADMIN_USERNAME)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    apply_schema_updates(engine)
    with SessionLocal() as db:
        _seed_roles(db)
        _seed_admin(db)
        seed_catalog(db)
        seed_document_templates(db)
        SettingsService(db).get()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()

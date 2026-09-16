from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import Practitioner, Role, RoleCode, User
from app.repositories.practitioner_repository import PractitionerRepository
from app.repositories.user_repository import RoleRepository, UserRepository
from app.schemas.user import UserAdminUpdate, UserCreate
from app.services.exceptions import BusinessRuleError, ConflictError, NotFoundError

MAX_PAGE_SIZE = 100


class UserAdminService:
    """Gestión de usuarios del sistema (perfil ADMIN)."""

    def __init__(self, db: Session) -> None:
        self.users = UserRepository(db)
        self.roles = RoleRepository(db)
        self.practitioners = PractitionerRepository(db)

    def list_roles(self) -> list[Role]:
        return self.roles.list_active()

    def list_users(
        self,
        *,
        term: str | None,
        role_code: str | None,
        is_active: bool | None,
        page: int,
        page_size: int,
    ) -> tuple[list[User], int]:
        return self.users.search(
            term=term,
            role_code=role_code,
            is_active=is_active,
            page=max(page, 1),
            page_size=min(max(page_size, 1), MAX_PAGE_SIZE),
        )

    def get(self, user_id: int) -> User:
        user = self.users.get_by_id(user_id)
        if user is None or user.is_system:
            # La cuenta de soporte queda oculta también por id: no se edita, ni
            # se desactiva, ni se le puede reiniciar la contraseña desde la app.
            raise NotFoundError("El usuario no existe")
        return user

    def create(self, payload: UserCreate) -> User:
        email = payload.email.strip().lower()
        self._ensure_unique(payload.username, email)
        role = self._resolve_role(payload.role)

        user = self.users.create(
            User(
                username=payload.username,
                email=email,
                full_name=payload.full_name,
                password_hash=hash_password(payload.password),
                role_id=role.id,
                is_active=payload.is_active,
            )
        )
        self._sync_practitioner(user)
        return user

    def update(self, user_id: int, payload: UserAdminUpdate, actor: User) -> User:
        user = self.get(user_id)
        email = payload.email.strip().lower()
        self._ensure_unique(payload.username, email, exclude_id=user.id)
        role = self._resolve_role(payload.role)

        is_self = user.id == actor.id
        if is_self and not payload.is_active:
            raise BusinessRuleError("No puede desactivar su propia cuenta")
        if is_self and role.code != user.role:
            raise BusinessRuleError("No puede cambiar su propio perfil de acceso")

        losing_admin = user.role == RoleCode.ADMIN.value and (
            role.code != RoleCode.ADMIN.value or not payload.is_active
        )
        if losing_admin and self.users.count_active_by_role(RoleCode.ADMIN.value, user.id) == 0:
            raise BusinessRuleError("Debe existir al menos un administrador activo")

        user.username = payload.username
        user.email = email
        user.full_name = payload.full_name
        user.role_id = role.id
        user.is_active = payload.is_active
        user = self.users.save(user)
        self._sync_practitioner(user)
        return user

    def set_active(self, user_id: int, is_active: bool, actor: User) -> User:
        user = self.get(user_id)
        if user.id == actor.id:
            raise BusinessRuleError("No puede desactivar su propia cuenta")
        if (
            not is_active
            and user.role == RoleCode.ADMIN.value
            and self.users.count_active_by_role(RoleCode.ADMIN.value, user.id) == 0
        ):
            raise BusinessRuleError("Debe existir al menos un administrador activo")

        user.is_active = is_active
        user = self.users.save(user)
        self._sync_practitioner(user)
        return user

    def reset_password(self, user_id: int, new_password: str) -> User:
        user = self.get(user_id)
        user.password_hash = hash_password(new_password)
        return self.users.save(user)

    def _sync_practitioner(self, user: User) -> None:
        """Mantiene la ficha de profesional de quien tiene perfil Médico.

        Sin esto, crear el usuario no bastaba: el médico no figuraba en
        Profesionales, así que no aparecía en los selectores de la agenda y no
        se le podían asignar citas hasta darlo de alta a mano por segunda vez.
        """
        practitioner = self.practitioners.get_by_user(user.id)

        if user.role != RoleCode.MEDICO.value:
            # Al dejar de ser médico se retira de la agenda, pero la ficha se
            # conserva: las citas y atenciones ya registradas la referencian.
            if practitioner is not None and practitioner.is_active:
                practitioner.is_active = False
                self.practitioners.save(practitioner)
            return

        if practitioner is None:
            # Si ya existía una ficha suelta con ese nombre se vincula, para no
            # duplicar al mismo médico en la agenda.
            practitioner = self.practitioners.find_unlinked_by_name(user.full_name)
            if practitioner is None:
                practitioner = Practitioner(full_name=user.full_name, email=user.email)
            practitioner.user_id = user.id

        practitioner.is_active = user.is_active
        self.practitioners.save(practitioner)

    def _ensure_unique(self, username: str, email: str, exclude_id: int | None = None) -> None:
        if self.users.username_taken(username, exclude_id=exclude_id):
            raise ConflictError("El nombre de usuario ya está en uso")
        if self.users.email_taken(email, exclude_id=exclude_id):
            raise ConflictError("El correo ya está registrado por otro usuario")

    def _resolve_role(self, code: str) -> Role:
        role = self.roles.get_by_code(code.strip().upper())
        if role is None or not role.is_active:
            raise BusinessRuleError("El perfil de acceso indicado no es válido")
        return role

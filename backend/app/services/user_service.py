from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import PasswordChange, ProfileUpdate
from app.services.exceptions import (
    BusinessRuleError,
    ConflictError,
    InvalidCurrentPasswordError,
)


class UserService:
    """Operaciones que un usuario realiza sobre su propia cuenta."""

    def __init__(self, db: Session) -> None:
        self.users = UserRepository(db)

    @staticmethod
    def _ensure_editable(user: User) -> None:
        """La cuenta de soporte se define en el entorno.

        Permitir cambiarla desde la aplicación solo confundiría: el sembrado
        la devuelve a los valores de FIRST_ADMIN_* en el siguiente arranque.
        """
        if user.is_system:
            raise BusinessRuleError(
                "La cuenta de soporte técnico se configura por variables de entorno"
            )

    def update_profile(self, user: User, payload: ProfileUpdate) -> User:
        self._ensure_editable(user)
        email = payload.email.strip().lower()

        if self.users.username_taken(payload.username, exclude_id=user.id):
            raise ConflictError("El nombre de usuario ya está en uso")
        if self.users.email_taken(email, exclude_id=user.id):
            raise ConflictError("El correo ya está registrado por otro usuario")

        user.full_name = payload.full_name
        user.email = email
        user.username = payload.username
        return self.users.save(user)

    def change_password(self, user: User, payload: PasswordChange) -> User:
        self._ensure_editable(user)
        if not verify_password(payload.current_password, user.password_hash):
            raise InvalidCurrentPasswordError
        if verify_password(payload.new_password, user.password_hash):
            raise BusinessRuleError("La nueva contraseña debe ser distinta a la actual")

        user.password_hash = hash_password(payload.new_password)
        return self.users.save(user)

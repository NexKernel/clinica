from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.models import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenResponse
from app.schemas.user import UserRead
from app.services.exceptions import InactiveUserError, InvalidCredentialsError


class AuthService:
    def __init__(self, db: Session) -> None:
        self.users = UserRepository(db)

    def authenticate(self, identifier: str, password: str) -> User:
        user = self.users.get_by_identifier(identifier)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError
        if not user.is_active:
            raise InactiveUserError
        return user

    def login(self, identifier: str, password: str) -> TokenResponse:
        user = self.authenticate(identifier, password)
        token, expires_in = create_access_token(
            user.id, extra_claims={"role": user.role, "username": user.username}
        )
        return TokenResponse(
            access_token=token,
            expires_in=expires_in,
            user=UserRead.model_validate(user),
        )

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.models import Role, User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_identifier(self, identifier: str) -> User | None:
        value = identifier.strip().lower()
        stmt = select(User).where(
            or_(
                func.lower(User.username) == value,
                func.lower(User.email) == value,
            )
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def username_taken(self, username: str, exclude_id: int | None = None) -> bool:
        return self._exists(func.lower(User.username) == username.strip().lower(), exclude_id)

    def email_taken(self, email: str, exclude_id: int | None = None) -> bool:
        return self._exists(func.lower(User.email) == email.strip().lower(), exclude_id)

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def save(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def search(
        self,
        *,
        term: str | None = None,
        role_code: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[User], int]:
        stmt = self._apply_filters(select(User).join(User.role_ref), term, role_code, is_active)

        total = self.db.execute(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        ).scalar_one()

        stmt = (
            stmt.order_by(User.is_active.desc(), User.full_name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(self.db.execute(stmt).unique().scalars().all())
        return items, total

    def count_active_by_role(self, role_code: str, exclude_id: int | None = None) -> int:
        stmt = (
            select(func.count(User.id))
            .join(User.role_ref)
            .where(Role.code == role_code, User.is_active.is_(True))
        )
        if exclude_id is not None:
            stmt = stmt.where(User.id != exclude_id)
        return self.db.execute(stmt).scalar_one()

    @staticmethod
    def _apply_filters(
        stmt: Select[tuple[User]],
        term: str | None,
        role_code: str | None,
        is_active: bool | None,
    ) -> Select[tuple[User]]:
        if term:
            pattern = f"%{term.strip().lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(User.full_name).like(pattern),
                    func.lower(User.username).like(pattern),
                    func.lower(User.email).like(pattern),
                )
            )
        if role_code:
            stmt = stmt.where(Role.code == role_code)
        if is_active is not None:
            stmt = stmt.where(User.is_active.is_(is_active))
        return stmt

    def _exists(self, condition: ColumnElement[bool], exclude_id: int | None) -> bool:
        stmt = select(User.id).where(condition)
        if exclude_id is not None:
            stmt = stmt.where(User.id != exclude_id)
        return self.db.execute(stmt).first() is not None


class RoleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_code(self, code: str) -> Role | None:
        stmt = select(Role).where(Role.code == code)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_active(self) -> list[Role]:
        stmt = select(Role).where(Role.is_active.is_(True)).order_by(Role.id)
        return list(self.db.execute(stmt).scalars().all())

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.license_scope import apply_license_scope, license_scope_for_user
from app.models.rol import Rol
from app.schemas.rol import RolPublic
from app.schemas.user import UserPublic


class RolNotFoundError(Exception):
    pass


class RolService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def to_public(row: Rol) -> RolPublic:
        return RolPublic(
            id=str(row.id),
            rol=row.rol,
            licenseId=row.license_id,
            added_date=row.added_date,
            updated_date=row.updated_date,
        )

    def list_all(self, user: UserPublic) -> list[RolPublic]:
        stmt = select(Rol).order_by(Rol.id)
        stmt = apply_license_scope(stmt, Rol, license_scope_for_user(user))
        return [self.to_public(row) for row in self.db.scalars(stmt).all()]

    def get_by_id(self, rol_id: int, user: UserPublic) -> RolPublic:
        stmt = apply_license_scope(
            select(Rol).where(Rol.id == rol_id),
            Rol,
            license_scope_for_user(user),
        )
        row = self.db.scalars(stmt).first()
        if row is None:
            raise RolNotFoundError()
        return self.to_public(row)

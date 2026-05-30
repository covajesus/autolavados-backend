from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.datetime_utils import business_now
from app.core.license_scope import license_scope_for_user
from app.core.roles import SUPER_ADMIN_ROL_ID
from app.models.license import License
from app.schemas.license import LicenseCreate, LicensePublic, LicenseUpdate
from app.schemas.user import UserPublic


class LicenseNotFoundError(Exception):
    pass


class LicenseValidationError(Exception):
    pass


class LicenseService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _now() -> datetime:
        return business_now()

    @staticmethod
    def _validate_dates(since_date: date | None, end_date: date | None) -> None:
        if since_date is not None and end_date is not None and end_date < since_date:
            raise LicenseValidationError("La fecha de fin no puede ser anterior al inicio")

    @staticmethod
    def to_public(row: License) -> LicensePublic:
        return LicensePublic(
            id=str(row.id),
            license_client_name=row.license_client_name,
            since_date=row.since_date,
            end_date=row.end_date,
            added_date=row.added_date,
            updated_date=row.updated_date,
            deleted_date=row.deleted_date,
        )

    def _active_filter(self, stmt):
        return stmt.where(License.deleted_date.is_(None))

    def _find_duplicate(
        self,
        name: str,
        except_id: int | None = None,
    ) -> License | None:
        normalized = name.strip().lower()
        stmt = self._active_filter(select(License)).where(
            func.lower(License.license_client_name) == normalized,
        )
        if except_id is not None:
            stmt = stmt.where(License.id != except_id)
        return self.db.scalars(stmt).first()

    @staticmethod
    def _is_super_admin(user: UserPublic) -> bool:
        return user.roleId == SUPER_ADMIN_ROL_ID

    def list_all(self, user: UserPublic) -> list[LicensePublic]:
        if self._is_super_admin(user):
            stmt = self._active_filter(select(License)).order_by(License.license_client_name)
            return [self.to_public(row) for row in self.db.scalars(stmt).all()]

        stmt = self._active_filter(select(License)).order_by(License.license_client_name)
        scope = license_scope_for_user(user)
        if scope == 0:
            return []
        if scope is not None:
            stmt = stmt.where(License.id == scope)
        return [self.to_public(row) for row in self.db.scalars(stmt).all()]

    def get_by_id(self, license_id: int, user: UserPublic | None = None) -> LicensePublic:
        if user is not None and not self._is_super_admin(user):
            scope = license_scope_for_user(user)
            if scope == 0 or (scope is not None and scope != license_id):
                raise LicenseNotFoundError()
        stmt = self._active_filter(select(License)).where(License.id == license_id)
        row = self.db.scalars(stmt).first()
        if row is None:
            raise LicenseNotFoundError()
        return self.to_public(row)

    def create(self, data: LicenseCreate, user: UserPublic) -> LicensePublic:
        if not self._is_super_admin(user):
            raise LicenseValidationError("No autorizado")
        name = data.license_client_name.strip()
        if not name:
            raise LicenseValidationError("El nombre del cliente es obligatorio")
        self._validate_dates(data.since_date, data.end_date)
        if self._find_duplicate(name):
            raise LicenseValidationError("Ya existe una licencia con ese cliente")

        now = self._now()
        row = License(
            license_client_name=name,
            since_date=data.since_date,
            end_date=data.end_date,
            added_date=now,
            updated_date=now,
            deleted_date=None,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self.to_public(row)

    def update(self, license_id: int, data: LicenseUpdate, user: UserPublic) -> LicensePublic:
        if not self._is_super_admin(user):
            raise LicenseNotFoundError()
        row = self.db.get(License, license_id)
        if row is None or not row.is_active:
            raise LicenseNotFoundError()

        if data.license_client_name is not None:
            name = data.license_client_name.strip()
            if not name:
                raise LicenseValidationError("El nombre del cliente no puede quedar vacío")
            if self._find_duplicate(name, except_id=license_id):
                raise LicenseValidationError("Ya existe una licencia con ese cliente")
            row.license_client_name = name

        if data.since_date is not None:
            row.since_date = data.since_date

        if data.end_date is not None:
            row.end_date = data.end_date

        self._validate_dates(row.since_date, row.end_date)

        row.updated_date = self._now()
        self.db.commit()
        self.db.refresh(row)
        return self.to_public(row)

    def delete(self, license_id: int, user: UserPublic) -> None:
        if not self._is_super_admin(user):
            raise LicenseNotFoundError()
        row = self.db.get(License, license_id)
        if row is None or not row.is_active:
            raise LicenseNotFoundError()

        now = self._now()
        row.deleted_date = now
        row.updated_date = now
        self.db.commit()

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.datetime_utils import datetime_to_iso, business_now
from app.core.license_scope import (
    apply_license_scope,
    assert_row_license,
    effective_license_id_for_write,
    license_scope_for_user,
)
from app.models.status import Status
from app.schemas.status import StatusCreate, StatusPublic, StatusUpdate
from app.schemas.user import UserPublic


class StatusNotFoundError(Exception):
    pass


class StatusValidationError(Exception):
    pass


class StatusService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _now() -> datetime:
        return business_now()

    @staticmethod
    def to_public(row: Status) -> StatusPublic:
        return StatusPublic(
            id=str(row.id),
            status=row.status,
            licenseId=row.license_id,
            added_date=datetime_to_iso(row.added_date),
            updated_date=datetime_to_iso(row.updated_date),
            deleted_date=datetime_to_iso(row.deleted_date),
        )

    def _active_filter(self, stmt):
        return stmt.where(Status.deleted_date.is_(None))

    def _find_duplicate(
        self,
        status_text: str,
        license_id: int | None,
        except_id: int | None = None,
    ) -> Status | None:
        normalized = status_text.strip().lower()
        stmt = self._active_filter(select(Status)).where(
            func.lower(Status.status) == normalized,
            Status.license_id == license_id,
        )
        if except_id is not None:
            stmt = stmt.where(Status.id != except_id)
        return self.db.scalars(stmt).first()

    def list_all(self, user: UserPublic) -> list[StatusPublic]:
        stmt = self._active_filter(select(Status)).order_by(Status.status)
        stmt = apply_license_scope(stmt, Status, license_scope_for_user(user))
        rows = self.db.scalars(stmt).all()
        return [self.to_public(row) for row in rows]

    def get_by_id(self, status_id: int, user: UserPublic) -> StatusPublic:
        stmt = self._active_filter(select(Status)).where(Status.id == status_id)
        stmt = apply_license_scope(stmt, Status, license_scope_for_user(user))
        row = self.db.scalars(stmt).first()
        if row is None:
            raise StatusNotFoundError()
        return self.to_public(row)

    def create(self, data: StatusCreate, user: UserPublic) -> StatusPublic:
        text = data.status.strip()
        if not text:
            raise StatusValidationError("El estatus es obligatorio")
        license_id = effective_license_id_for_write(
            self.db,
            user,
            data.licenseId,
            error_factory=StatusValidationError,
        )
        if self._find_duplicate(text, license_id):
            raise StatusValidationError("Ya existe un estatus con ese nombre")

        now = self._now()
        row = Status(
            status=text,
            license_id=license_id,
            added_date=now,
            updated_date=now,
            deleted_date=None,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self.to_public(row)

    def update(self, status_id: int, data: StatusUpdate, user: UserPublic) -> StatusPublic:
        row = self.db.get(Status, status_id)
        if row is None or not row.is_active:
            raise StatusNotFoundError()
        scope = license_scope_for_user(user)
        assert_row_license(row, scope, not_found_exc=StatusNotFoundError)

        if data.status is not None:
            text = data.status.strip()
            if not text:
                raise StatusValidationError("El estatus no puede quedar vacío")
            row.status = text

        if data.licenseId is not None or scope is not None:
            row.license_id = effective_license_id_for_write(
                self.db,
                user,
                data.licenseId,
                error_factory=StatusValidationError,
            )

        if self._find_duplicate(row.status, row.license_id, except_id=status_id):
            raise StatusValidationError("Ya existe un estatus con ese nombre")

        row.updated_date = self._now()
        self.db.commit()
        self.db.refresh(row)
        return self.to_public(row)

    def delete(self, status_id: int, user: UserPublic) -> None:
        row = self.db.get(Status, status_id)
        if row is None or not row.is_active:
            raise StatusNotFoundError()
        assert_row_license(row, license_scope_for_user(user), not_found_exc=StatusNotFoundError)

        now = self._now()
        row.deleted_date = now
        row.updated_date = now
        self.db.commit()

from datetime import datetime

from app.core.datetime_utils import business_now
from app.core.license_scope import (
    apply_license_scope,
    assert_row_license,
    effective_license_id_for_write,
    license_scope_for_user,
)

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.branch_office import BranchOffice
from app.schemas.branch_office import BranchOfficeCreate, BranchOfficePublic, BranchOfficeUpdate
from app.schemas.user import UserPublic


class BranchOfficeNotFoundError(Exception):
    pass


class BranchOfficeValidationError(Exception):
    pass


class BranchOfficeService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _now() -> datetime:
        return business_now()

    @staticmethod
    def _management_type_id(row: BranchOffice) -> int:
        value = getattr(row, "management_type_id", None)
        if value in (1, 2):
            return int(value)
        return 1

    @staticmethod
    def _validate_management_type(management_type_id: int) -> None:
        if management_type_id not in (1, 2):
            raise BranchOfficeValidationError(
                "Tipo de gestión inválido (use 1 Administrada o 2 Subarriendo)",
            )

    @staticmethod
    def to_public(row: BranchOffice) -> BranchOfficePublic:
        return BranchOfficePublic(
            id=str(row.id),
            name=row.branch_office,
            active=row.is_active,
            licenseId=row.license_id,
            managementTypeId=BranchOfficeService._management_type_id(row),
        )

    def list_all(self, user: UserPublic) -> list[BranchOfficePublic]:
        stmt = select(BranchOffice).order_by(BranchOffice.id)
        stmt = apply_license_scope(stmt, BranchOffice, license_scope_for_user(user))
        rows = self.db.scalars(stmt).all()
        return [self.to_public(row) for row in rows]

    def get_by_id(self, branch_id: int, user: UserPublic) -> BranchOfficePublic:
        row = self.db.get(BranchOffice, branch_id)
        if row is None:
            raise BranchOfficeNotFoundError()
        assert_row_license(row, license_scope_for_user(user), not_found_exc=BranchOfficeNotFoundError)
        return self.to_public(row)

    def create(self, data: BranchOfficeCreate, user: UserPublic) -> BranchOfficePublic:
        name = data.name.strip()
        if not name:
            raise BranchOfficeValidationError("La sucursal es obligatoria")
        self._validate_management_type(data.managementTypeId)
        license_id = effective_license_id_for_write(
            self.db,
            user,
            data.licenseId,
            error_factory=BranchOfficeValidationError,
        )

        now = self._now()
        row = BranchOffice(
            branch_office=name,
            license_id=license_id,
            management_type_id=data.managementTypeId,
            added_date=now,
            updated_date=now,
            deleted_date=None if data.active else now,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self.to_public(row)

    def update(self, branch_id: int, data: BranchOfficeUpdate, user: UserPublic) -> BranchOfficePublic:
        row = self.db.get(BranchOffice, branch_id)
        if row is None:
            raise BranchOfficeNotFoundError()
        scope = license_scope_for_user(user)
        assert_row_license(row, scope, not_found_exc=BranchOfficeNotFoundError)

        if data.name is not None:
            name = data.name.strip()
            if not name:
                raise BranchOfficeValidationError("La sucursal no puede quedar vacía")
            row.branch_office = name

        if data.active is not None:
            row.deleted_date = None if data.active else self._now()

        if data.licenseId is not None or scope is not None:
            row.license_id = effective_license_id_for_write(
                self.db,
                user,
                data.licenseId,
                error_factory=BranchOfficeValidationError,
            )

        if data.managementTypeId is not None:
            self._validate_management_type(data.managementTypeId)
            row.management_type_id = data.managementTypeId

        row.updated_date = self._now()
        self.db.commit()
        self.db.refresh(row)
        return self.to_public(row)

    def delete(self, branch_id: int, user: UserPublic) -> None:
        row = self.db.get(BranchOffice, branch_id)
        if row is None:
            raise BranchOfficeNotFoundError()
        assert_row_license(row, license_scope_for_user(user), not_found_exc=BranchOfficeNotFoundError)

        now = self._now()
        row.deleted_date = now
        row.updated_date = now
        self.db.commit()

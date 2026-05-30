import re
from datetime import datetime

from app.core.datetime_utils import business_now
from app.core.license_scope import (
    apply_license_scope,
    assert_row_license,
    effective_license_id_for_write,
    license_scope_for_user,
)

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerPublic, CustomerUpdate
from app.schemas.user import UserPublic

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class CustomerNotFoundError(Exception):
    pass


class CustomerValidationError(Exception):
    pass


class CustomerService:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _now() -> datetime:
        return business_now()

    @staticmethod
    def to_public(row: Customer) -> CustomerPublic:
        return CustomerPublic(
            id=str(row.id),
            license_plate_id=row.license_plate_id,
            full_name=row.full_name,
            phone=row.phone,
            email=row.email,
            licenseId=row.license_id,
            added_date=row.added_date,
            updated_date=row.updated_date,
            deleted_date=row.deleted_date,
        )

    def _active_filter(self, stmt):
        return stmt.where(Customer.deleted_date.is_(None))

    def _find_by_plate(
        self,
        plate: str,
        license_id: int | None,
        except_id: int | None = None,
    ) -> Customer | None:
        normalized = plate.strip().upper()
        stmt = self._active_filter(select(Customer)).where(
            func.upper(Customer.license_plate_id) == normalized,
            Customer.license_id == license_id,
        )
        if except_id is not None:
            stmt = stmt.where(Customer.id != except_id)
        return self.db.scalars(stmt).first()

    def list_all(self, user: UserPublic) -> list[CustomerPublic]:
        stmt = self._active_filter(select(Customer)).order_by(Customer.added_date.desc())
        stmt = apply_license_scope(stmt, Customer, license_scope_for_user(user))
        return [self.to_public(row) for row in self.db.scalars(stmt).all()]

    def get_by_id(self, customer_id: int, user: UserPublic) -> CustomerPublic:
        stmt = self._active_filter(select(Customer)).where(Customer.id == customer_id)
        stmt = apply_license_scope(stmt, Customer, license_scope_for_user(user))
        row = self.db.scalars(stmt).first()
        if row is None:
            raise CustomerNotFoundError()
        return self.to_public(row)

    def get_by_license_plate(self, license_plate_id: str, user: UserPublic) -> CustomerPublic | None:
        normalized = license_plate_id.strip().upper()
        stmt = self._active_filter(select(Customer)).where(
            func.upper(Customer.license_plate_id) == normalized,
        )
        stmt = apply_license_scope(stmt, Customer, license_scope_for_user(user))
        row = self.db.scalars(stmt).first()
        return self.to_public(row) if row else None

    def create(self, data: CustomerCreate, user: UserPublic) -> CustomerPublic:
        plate = data.license_plate_id.strip()
        if not plate:
            raise CustomerValidationError("La placa es obligatoria")
        license_id = effective_license_id_for_write(
            self.db,
            user,
            data.licenseId,
            error_factory=CustomerValidationError,
        )
        if self._find_by_plate(plate, license_id):
            raise CustomerValidationError("Ya existe un cliente con esa placa")

        full_name = data.full_name.strip()
        if not full_name:
            raise CustomerValidationError("El nombre completo es obligatorio")

        email = (data.email or "").strip()
        if email and not _EMAIL_RE.match(email):
            raise CustomerValidationError("El correo electrónico no es válido")

        now = self._now()
        row = Customer(
            license_plate_id=plate,
            full_name=full_name,
            phone=(data.phone or "").strip(),
            email=email,
            license_id=license_id,
            added_date=now,
            updated_date=now,
            deleted_date=None,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self.to_public(row)

    def update(self, customer_id: int, data: CustomerUpdate, user: UserPublic) -> CustomerPublic:
        row = self.db.get(Customer, customer_id)
        if row is None or not row.is_active:
            raise CustomerNotFoundError()
        scope = license_scope_for_user(user)
        assert_row_license(row, scope, not_found_exc=CustomerNotFoundError)

        if data.license_plate_id is not None:
            plate = data.license_plate_id.strip()
            if not plate:
                raise CustomerValidationError("La placa no puede quedar vacía")
            row.license_plate_id = plate

        if data.full_name is not None:
            name = data.full_name.strip()
            if not name:
                raise CustomerValidationError("El nombre completo no puede quedar vacío")
            row.full_name = name

        if data.phone is not None:
            row.phone = data.phone.strip()

        if data.email is not None:
            email = data.email.strip()
            if email and not _EMAIL_RE.match(email):
                raise CustomerValidationError("El correo electrónico no es válido")
            row.email = email

        if data.licenseId is not None or scope is not None:
            row.license_id = effective_license_id_for_write(
                self.db,
                user,
                data.licenseId,
                error_factory=CustomerValidationError,
            )

        if self._find_by_plate(row.license_plate_id, row.license_id, except_id=customer_id):
            raise CustomerValidationError("Ya existe un cliente con esa placa")

        row.updated_date = self._now()
        self.db.commit()
        self.db.refresh(row)
        return self.to_public(row)

    def delete(self, customer_id: int, user: UserPublic) -> None:
        row = self.db.get(Customer, customer_id)
        if row is None or not row.is_active:
            raise CustomerNotFoundError()
        assert_row_license(row, license_scope_for_user(user), not_found_exc=CustomerNotFoundError)
        now = self._now()
        row.deleted_date = now
        row.updated_date = now
        self.db.commit()

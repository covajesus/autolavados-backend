from collections.abc import Callable
from datetime import date
from typing import Any, TypeVar

from sqlalchemy import false
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from app.core.datetime_utils import business_today
from app.core.license_helpers import resolve_license_id
from app.models.license import License
from app.schemas.user import UserPublic

T = TypeVar("T", bound=Exception)


def license_scope_for_user(user: UserPublic) -> int | None:
    """
    None: sin filtro (admin plataforma sin licenseId).
    int >= 1: solo datos de esa licencia.
    0: usuario sin licencia → sin acceso a datos tenant.
    """
    license_id = user.licenseId
    if license_id is not None and license_id >= 1:
        return license_id
    if user.role == "admin":
        return None
    return 0


def is_platform_admin(user: UserPublic) -> bool:
    return user.role == "admin" and license_scope_for_user(user) is None


def license_is_usable(license_row: License, *, on_date: date | None = None) -> bool:
    """Sin end_date la licencia no vence. Con end_date, válida hasta ese día inclusive."""
    if not license_row.is_active:
        return False
    if license_row.end_date is None:
        return True
    today = on_date or business_today()
    return today <= license_row.end_date


def apply_license_scope(
    stmt: Select[Any],
    model: Any,
    license_id: int | None,
    *,
    column: Any | None = None,
) -> Select[Any]:
    col = column if column is not None else model.license_id
    if license_id is None:
        return stmt
    if license_id == 0:
        return stmt.where(false())
    return stmt.where(col == license_id)


def assert_row_license(
    row: Any,
    license_id: int | None,
    *,
    not_found_exc: type[Exception],
) -> None:
    if license_id is None:
        return
    if license_id == 0 or getattr(row, "license_id", None) != license_id:
        raise not_found_exc()


def effective_license_id_for_write(
    db: Session,
    user: UserPublic,
    requested: int | None,
    *,
    error_factory: Callable[[str], T],
) -> int | None:
    scope = license_scope_for_user(user)
    if scope is not None and scope >= 1:
        return scope
    if scope == 0:
        raise error_factory("Su cuenta no tiene licencia asignada")
    return resolve_license_id(db, requested, error_factory=error_factory)

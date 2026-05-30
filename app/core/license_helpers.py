from collections.abc import Callable
from typing import TypeVar

from sqlalchemy.orm import Session

from app.models.branch_office import BranchOffice

T = TypeVar("T", bound=Exception)


def resolve_license_id(
    db: Session,
    license_id_raw: int | None,
    *,
    error_factory: Callable[[str], T],
) -> int | None:
    if license_id_raw is None:
        return None
    if license_id_raw < 1:
        raise error_factory("La licencia no es válida")
    from app.services.license_service import LicenseNotFoundError, LicenseService

    try:
        LicenseService(db).get_by_id(license_id_raw)
    except LicenseNotFoundError as exc:
        raise error_factory("La licencia no existe") from exc
    return license_id_raw


def license_id_from_branch(db: Session, branch_office_id: int | None) -> int | None:
    if branch_office_id is None or branch_office_id < 1:
        return None
    branch = db.get(BranchOffice, branch_office_id)
    if branch is None:
        return None
    return branch.license_id

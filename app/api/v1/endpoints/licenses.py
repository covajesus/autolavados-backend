from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserDep, LicenseServiceDep
from app.schemas.license import (
    ErrorResponse,
    LicenseCreate,
    LicenseDeleteResponse,
    LicenseItemResponse,
    LicenseListResponse,
    LicenseUpdate,
)
from app.services.license_service import LicenseNotFoundError, LicenseValidationError

router = APIRouter(prefix="/licenses", tags=["licenses"])


@router.get("", response_model=LicenseListResponse)
def list_licenses(service: LicenseServiceDep, current_user: CurrentUserDep) -> LicenseListResponse:
    return LicenseListResponse(items=service.list_all(current_user))


@router.post("", response_model=LicenseItemResponse, status_code=status.HTTP_201_CREATED)
def create_license(
    body: LicenseCreate,
    service: LicenseServiceDep,
    current_user: CurrentUserDep,
) -> LicenseItemResponse:
    try:
        return LicenseItemResponse(item=service.create(body, current_user))
    except LicenseValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/{license_id}",
    response_model=LicenseItemResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_license(
    license_id: int,
    service: LicenseServiceDep,
    current_user: CurrentUserDep,
) -> LicenseItemResponse:
    try:
        return LicenseItemResponse(item=service.get_by_id(license_id, current_user))
    except LicenseNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No encontrado") from exc


@router.patch(
    "/{license_id}",
    response_model=LicenseItemResponse,
    responses={404: {"model": ErrorResponse}},
)
def update_license(
    license_id: int,
    body: LicenseUpdate,
    service: LicenseServiceDep,
    current_user: CurrentUserDep,
) -> LicenseItemResponse:
    try:
        return LicenseItemResponse(item=service.update(license_id, body, current_user))
    except LicenseNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No encontrado") from exc
    except LicenseValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete(
    "/{license_id}",
    response_model=LicenseDeleteResponse,
    responses={404: {"model": ErrorResponse}},
)
def delete_license(
    license_id: int,
    service: LicenseServiceDep,
    current_user: CurrentUserDep,
) -> LicenseDeleteResponse:
    try:
        service.delete(license_id, current_user)
    except LicenseNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No encontrado") from exc
    return LicenseDeleteResponse()

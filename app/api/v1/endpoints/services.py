from fastapi import APIRouter, HTTPException, status

from app.api.deps import CatalogServiceDep, CurrentUserDep
from app.schemas.service import (
    ErrorResponse,
    ServiceCreate,
    ServiceDeleteResponse,
    ServiceItemResponse,
    ServiceListResponse,
    ServiceUpdate,
)
from app.services.catalog_service import ServiceNotFoundError, ServiceValidationError

router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=ServiceListResponse)
def list_services(service: CatalogServiceDep, current_user: CurrentUserDep) -> ServiceListResponse:
    return ServiceListResponse(items=service.list_all(current_user))


@router.post("", response_model=ServiceItemResponse, status_code=status.HTTP_201_CREATED)
def create_service(
    body: ServiceCreate,
    service: CatalogServiceDep,
    current_user: CurrentUserDep,
) -> ServiceItemResponse:
    try:
        return ServiceItemResponse(item=service.create(body, current_user))
    except ServiceValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{service_id}", response_model=ServiceItemResponse, responses={404: {"model": ErrorResponse}})
def get_service(
    service_id: int,
    service: CatalogServiceDep,
    current_user: CurrentUserDep,
) -> ServiceItemResponse:
    try:
        return ServiceItemResponse(item=service.get_by_id(service_id, current_user))
    except ServiceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No encontrado") from exc


@router.patch("/{service_id}", response_model=ServiceItemResponse, responses={404: {"model": ErrorResponse}})
def update_service(
    service_id: int,
    body: ServiceUpdate,
    service: CatalogServiceDep,
    current_user: CurrentUserDep,
) -> ServiceItemResponse:
    try:
        return ServiceItemResponse(item=service.update(service_id, body, current_user))
    except ServiceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No encontrado") from exc
    except ServiceValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{service_id}", response_model=ServiceDeleteResponse, responses={404: {"model": ErrorResponse}})
def delete_service(
    service_id: int,
    service: CatalogServiceDep,
    current_user: CurrentUserDep,
) -> ServiceDeleteResponse:
    try:
        service.delete(service_id, current_user)
    except ServiceNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No encontrado") from exc
    return ServiceDeleteResponse()

from fastapi import APIRouter, HTTPException, status

from app.api.deps import BrandServiceDep, CurrentUserDep
from app.schemas.brand import (
    BrandCreate,
    BrandDeleteResponse,
    BrandItemResponse,
    BrandListResponse,
    BrandUpdate,
    ErrorResponse,
)
from app.services.brand_service import BrandNotFoundError, BrandValidationError

router = APIRouter(prefix="/brands", tags=["brands"])


@router.get("", response_model=BrandListResponse)
def list_brands(service: BrandServiceDep, current_user: CurrentUserDep) -> BrandListResponse:
    return BrandListResponse(items=service.list_all(current_user))


@router.post("", response_model=BrandItemResponse, status_code=status.HTTP_201_CREATED)
def create_brand(
    body: BrandCreate,
    service: BrandServiceDep,
    current_user: CurrentUserDep,
) -> BrandItemResponse:
    try:
        return BrandItemResponse(item=service.create(body, current_user))
    except BrandValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{brand_id}", response_model=BrandItemResponse, responses={404: {"model": ErrorResponse}})
def get_brand(brand_id: int, service: BrandServiceDep, current_user: CurrentUserDep) -> BrandItemResponse:
    try:
        return BrandItemResponse(item=service.get_by_id(brand_id, current_user))
    except BrandNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No encontrado") from exc


@router.patch("/{brand_id}", response_model=BrandItemResponse, responses={404: {"model": ErrorResponse}})
def update_brand(
    brand_id: int,
    body: BrandUpdate,
    service: BrandServiceDep,
    current_user: CurrentUserDep,
) -> BrandItemResponse:
    try:
        return BrandItemResponse(item=service.update(brand_id, body, current_user))
    except BrandNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No encontrado") from exc
    except BrandValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{brand_id}", response_model=BrandDeleteResponse, responses={404: {"model": ErrorResponse}})
def delete_brand(
    brand_id: int,
    service: BrandServiceDep,
    current_user: CurrentUserDep,
) -> BrandDeleteResponse:
    try:
        service.delete(brand_id, current_user)
    except BrandNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No encontrado") from exc
    return BrandDeleteResponse()

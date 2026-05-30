from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUserDep, RolServiceDep
from app.schemas.rol import ErrorResponse, RolItemResponse, RolListResponse
from app.services.rol_service import RolNotFoundError

router = APIRouter(prefix="/roles", tags=["rols"])


@router.get("", response_model=RolListResponse)
def list_roles(service: RolServiceDep, current_user: CurrentUserDep) -> RolListResponse:
    return RolListResponse(items=service.list_all(current_user))


@router.get("/{rol_id}", response_model=RolItemResponse, responses={404: {"model": ErrorResponse}})
def get_role(rol_id: int, service: RolServiceDep, current_user: CurrentUserDep) -> RolItemResponse:
    try:
        return RolItemResponse(item=service.get_by_id(rol_id, current_user))
    except RolNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No encontrado") from exc

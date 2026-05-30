from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserDep, UserServiceDep
from app.schemas.user import (
    ErrorResponse,
    UserCreate,
    UserDeleteResponse,
    UserItemResponse,
    UserListResponse,
    UserUpdate,
)
from app.services.user_service import UserNotFoundError, UserValidationError

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=UserListResponse)
def list_users(
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> UserListResponse:
    return UserListResponse(items=service.list_all(current_user))


@router.get("/role/{rol_id}", response_model=UserListResponse)
def list_users_by_rol(
    rol_id: int,
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> UserListResponse:
    if rol_id < 1:
        raise HTTPException(status_code=400, detail="Rol no válido")
    return UserListResponse(items=service.list_by_rol_id(rol_id, current_user))


@router.get("/branch/{branch_office_id}/washers", response_model=UserListResponse)
def list_washers_by_branch(
    branch_office_id: int,
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> UserListResponse:
    if branch_office_id < 1:
        raise HTTPException(status_code=400, detail="Sucursal no válida")
    return UserListResponse(
        items=service.list_washers_by_branch_office(branch_office_id, current_user),
    )


@router.post("", response_model=UserItemResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> UserItemResponse:
    try:
        return UserItemResponse(item=service.create(body, current_user))
    except UserValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{user_id}", response_model=UserItemResponse, responses={404: {"model": ErrorResponse}})
def get_user(
    user_id: int,
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> UserItemResponse:
    try:
        return UserItemResponse(item=service.get_by_id(user_id, current_user))
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No encontrado") from exc


@router.patch("/{user_id}", response_model=UserItemResponse, responses={404: {"model": ErrorResponse}})
def update_user(
    user_id: int,
    body: UserUpdate,
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> UserItemResponse:
    try:
        return UserItemResponse(item=service.update(user_id, body, current_user))
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No encontrado") from exc
    except UserValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{user_id}", response_model=UserDeleteResponse, responses={404: {"model": ErrorResponse}})
def delete_user(
    user_id: int,
    current_user: CurrentUserDep,
    service: UserServiceDep,
) -> UserDeleteResponse:
    try:
        service.delete(user_id, current_user)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No encontrado") from exc
    return UserDeleteResponse()

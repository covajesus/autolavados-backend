from fastapi import APIRouter, HTTPException, status

from app.api.deps import ClientServiceDep, CurrentUserDep
from app.schemas.client import (
    ClientCreate,
    ClientDeleteResponse,
    ClientItemResponse,
    ClientListResponse,
    ClientUpdate,
    ErrorResponse,
)
from app.services.client_service import ClientNotFoundError, ClientValidationError

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=ClientListResponse)
def list_clients(service: ClientServiceDep, current_user: CurrentUserDep) -> ClientListResponse:
    return ClientListResponse(items=service.list_all(current_user))


@router.post("", response_model=ClientItemResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    body: ClientCreate,
    service: ClientServiceDep,
    current_user: CurrentUserDep,
) -> ClientItemResponse:
    try:
        return ClientItemResponse(item=service.create(body, current_user))
    except ClientValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/{client_id}",
    response_model=ClientItemResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_client(client_id: int, service: ClientServiceDep, current_user: CurrentUserDep) -> ClientItemResponse:
    try:
        return ClientItemResponse(item=service.get_by_id(client_id, current_user))
    except ClientNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No encontrado") from exc


@router.patch(
    "/{client_id}",
    response_model=ClientItemResponse,
    responses={404: {"model": ErrorResponse}},
)
def update_client(
    client_id: int,
    body: ClientUpdate,
    service: ClientServiceDep,
    current_user: CurrentUserDep,
) -> ClientItemResponse:
    try:
        return ClientItemResponse(item=service.update(client_id, body, current_user))
    except ClientNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No encontrado") from exc
    except ClientValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete(
    "/{client_id}",
    response_model=ClientDeleteResponse,
    responses={404: {"model": ErrorResponse}},
)
def delete_client(
    client_id: int,
    service: ClientServiceDep,
    current_user: CurrentUserDep,
) -> ClientDeleteResponse:
    try:
        service.delete(client_id, current_user)
    except ClientNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No encontrado") from exc
    return ClientDeleteResponse()

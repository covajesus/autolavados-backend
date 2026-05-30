from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUserDep, RaffleServiceDep
from app.core.license_scope import license_scope_for_user
from app.schemas.raffle import (
    ErrorResponse,
    RaffleCreate,
    RaffleCurrentResponse,
    RaffleDeleteResponse,
    RaffleDrawResponse,
    RaffleItemResponse,
    RaffleListResponse,
    RaffleNumberListResponse,
    RaffleUpdate,
)
from app.services.raffle_service import RaffleNotFoundError, RaffleValidationError

router = APIRouter(prefix="/raffles", tags=["raffles"])


@router.get(
    "",
    response_model=RaffleListResponse,
    responses={401: {"model": ErrorResponse}},
)
def list_raffles(service: RaffleServiceDep, current_user: CurrentUserDep) -> RaffleListResponse:
    return RaffleListResponse(items=service.list_all(current_user))


@router.get(
    "/current",
    response_model=RaffleCurrentResponse,
    responses={401: {"model": ErrorResponse}},
)
def get_current_raffle(
    service: RaffleServiceDep,
    current_user: CurrentUserDep,
) -> RaffleCurrentResponse:
    scope = license_scope_for_user(current_user)
    return RaffleCurrentResponse(
        item=None if scope == 0 else service.get_current_active_public(license_id=scope),
    )


@router.post(
    "",
    response_model=RaffleItemResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
)
def create_raffle(
    body: RaffleCreate,
    service: RaffleServiceDep,
    current_user: CurrentUserDep,
) -> RaffleItemResponse:
    try:
        item = service.create(body, current_user)
    except RaffleValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return RaffleItemResponse(item=item)


@router.get(
    "/{raffle_id}",
    response_model=RaffleItemResponse,
    responses={
        404: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
)
def get_raffle(
    raffle_id: int,
    service: RaffleServiceDep,
    current_user: CurrentUserDep,
) -> RaffleItemResponse:
    try:
        item = service.get_by_id(raffle_id, current_user)
    except RaffleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No encontrado",
        ) from exc
    return RaffleItemResponse(item=item)


@router.patch(
    "/{raffle_id}",
    response_model=RaffleItemResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
)
def update_raffle(
    raffle_id: int,
    body: RaffleUpdate,
    service: RaffleServiceDep,
    current_user: CurrentUserDep,
) -> RaffleItemResponse:
    try:
        item = service.update(raffle_id, body, current_user)
    except RaffleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No encontrado",
        ) from exc
    except RaffleValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return RaffleItemResponse(item=item)


@router.delete(
    "/{raffle_id}",
    response_model=RaffleDeleteResponse,
    responses={
        404: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
)
def delete_raffle(
    raffle_id: int,
    service: RaffleServiceDep,
    current_user: CurrentUserDep,
) -> RaffleDeleteResponse:
    try:
        service.delete(raffle_id, current_user)
    except RaffleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No encontrado",
        ) from exc
    return RaffleDeleteResponse()


@router.get(
    "/{raffle_id}/numbers",
    response_model=RaffleNumberListResponse,
    responses={
        404: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
)
def list_raffle_numbers(
    raffle_id: int,
    service: RaffleServiceDep,
    current_user: CurrentUserDep,
) -> RaffleNumberListResponse:
    try:
        items = service.list_numbers(raffle_id, current_user)
    except RaffleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No encontrado",
        ) from exc
    return RaffleNumberListResponse(items=items)


@router.get(
    "/{raffle_id}/draw",
    response_model=RaffleDrawResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
    },
)
def draw_raffle_number(
    raffle_id: int,
    service: RaffleServiceDep,
    current_user: CurrentUserDep,
    min_number: int = Query(default=1, ge=0, alias="min"),
    max_number: int = Query(default=9999, ge=1, alias="max"),
) -> RaffleDrawResponse:
    try:
        return service.draw_number(
            raffle_id,
            current_user,
            min_number=min_number,
            max_number=max_number,
        )
    except RaffleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No encontrado",
        ) from exc
    except RaffleValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

from fastapi import APIRouter

from fastapi import HTTPException, status

from app.api.deps import ConfigurationServiceDep, CurrentUserDep
from app.schemas.configuration import ConfigurationItemResponse, ErrorResponse
from app.services.configuration_service import ConfigurationValidationError

router = APIRouter(prefix="/configurations", tags=["configurations"])


@router.get(
    "",
    response_model=ConfigurationItemResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_configurations(
    service: ConfigurationServiceDep,
    current_user: CurrentUserDep,
) -> ConfigurationItemResponse:
    """Configuración pública del sitio web (contacto y redes)."""
    try:
        return ConfigurationItemResponse(item=service.get_settings(current_user))
    except ConfigurationValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

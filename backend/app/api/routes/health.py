from typing import Annotated

from fastapi import APIRouter, Depends

from backend.app.schemas.health import HealthResponse
from backend.app.services.health import HealthService

router = APIRouter(tags=["system"])


def get_health_service() -> HealthService:
    return HealthService()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    service: Annotated[HealthService, Depends(get_health_service)],
) -> HealthResponse:
    """Return a lightweight readiness response."""

    return service.get_status()

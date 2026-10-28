from backend.app.schemas.health import HealthResponse


class HealthService:
    """Provide application health information."""

    def get_status(self) -> HealthResponse:
        return HealthResponse(status="ok")

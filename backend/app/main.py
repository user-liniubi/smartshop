import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.api.router import api_router
from backend.app.core.config import Settings, get_settings
from backend.app.core.exceptions import register_exception_handlers
from backend.app.core.logging import configure_logging

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""

    application_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        configure_logging(application_settings.log_level)
        logger.info(
            "Starting %s in %s mode",
            application_settings.app_name,
            application_settings.app_env,
        )
        yield
        logger.info("Stopping %s", application_settings.app_name)

    application = FastAPI(
        title=application_settings.app_name,
        version="0.5.0",
        debug=application_settings.debug,
        lifespan=lifespan,
    )
    application.state.settings = application_settings
    register_exception_handlers(application)
    application.include_router(api_router)
    return application


app = create_app()

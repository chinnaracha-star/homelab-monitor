from fastapi import FastAPI

from homelab_monitor import __version__
from homelab_monitor.errors import APIError, api_error_handler
from homelab_monitor.logging import RequestLoggingMiddleware, configure_logging
from homelab_monitor.routers import agents, health
from homelab_monitor.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    application = FastAPI(
        title="HomeLab Monitor API",
        summary="Central API for HomeLab Monitor Toolkit agents and dashboard",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.add_exception_handler(APIError, api_error_handler)  # type: ignore[arg-type]
    application.add_middleware(RequestLoggingMiddleware)
    application.include_router(health.router)
    application.include_router(agents.router)
    return application


app = create_app()

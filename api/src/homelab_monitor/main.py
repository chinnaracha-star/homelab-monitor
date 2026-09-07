import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from homelab_monitor import __version__
from homelab_monitor.errors import APIError, api_error_handler
from homelab_monitor.logging import RequestLoggingMiddleware, configure_logging
from homelab_monitor.offline_monitor import run_offline_monitor
from homelab_monitor.routers import agents, auth, dashboard, health
from homelab_monitor.settings import get_settings


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(run_offline_monitor(get_settings()))
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    application = FastAPI(
        title="HomeLab Monitor API",
        summary="Central API for HomeLab Monitor Toolkit agents and dashboard",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    application.add_exception_handler(APIError, api_error_handler)  # type: ignore[arg-type]
    application.add_middleware(RequestLoggingMiddleware)
    application.include_router(health.router)
    application.include_router(auth.router)
    application.include_router(agents.router)
    application.include_router(dashboard.router)
    return application


app = create_app()

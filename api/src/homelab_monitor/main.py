import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from sqlalchemy.orm import Session

from homelab_monitor import __version__
from homelab_monitor.auth.bootstrap import ensure_default_users
from homelab_monitor.database import get_engine
from homelab_monitor.errors import APIError, api_error_handler
from homelab_monitor.infrastructure_monitor import run_infrastructure_monitor
from homelab_monitor.logging import RequestLoggingMiddleware, configure_logging
from homelab_monitor.notification_worker import run_notification_worker
from homelab_monitor.offline_monitor import run_offline_monitor
from homelab_monitor.realtime import hub
from homelab_monitor.routers import (
    agents,
    alert_history,
    alert_rules,
    analytics,
    auth,
    capacity,
    dashboard,
    developer,
    groups,
    health,
    history,
    incidents,
    infrastructure,
    insights,
    notifications,
    predictions,
    realtime,
    system,
    trends,
    users,
)
from homelab_monitor.settings import get_settings
from homelab_monitor.telegram_reports import run_telegram_reports


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    with Session(get_engine()) as db:
        ensure_default_users(db, get_settings())
    hub.bind_loop(asyncio.get_running_loop())
    tasks = [
        asyncio.create_task(run_offline_monitor(get_settings())),
        asyncio.create_task(run_infrastructure_monitor(get_settings())),
        asyncio.create_task(run_telegram_reports(get_settings())),
        asyncio.create_task(run_notification_worker(get_settings())),
    ]
    try:
        yield
    finally:
        hub.stop()
        for task in tasks:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_dir)

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
    application.include_router(history.router)
    application.include_router(users.router)
    application.include_router(groups.router)
    application.include_router(notifications.router)
    application.include_router(alert_rules.router)
    application.include_router(infrastructure.router)
    application.include_router(analytics.router)
    application.include_router(trends.router)
    application.include_router(capacity.router)
    application.include_router(developer.router)
    application.include_router(insights.router)
    application.include_router(alert_history.router)
    application.include_router(incidents.router)
    application.include_router(predictions.router)
    application.include_router(realtime.router)
    application.include_router(system.router)
    return application


app = create_app()

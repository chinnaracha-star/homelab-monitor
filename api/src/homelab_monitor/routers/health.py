from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from homelab_monitor import __version__
from homelab_monitor.database import get_db
from homelab_monitor.schemas import HealthResponse, PhotoMonitorHealth
from homelab_monitor.settings import get_settings

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Check API and database health",
)
def health(db: Annotated[Session, Depends(get_db)]) -> HealthResponse | JSONResponse:
    now = datetime.now(UTC)
    try:
        db.execute(text("SELECT COUNT(*) FROM agents"))
        db.execute(text("SELECT COUNT(*) FROM alerts"))
    except SQLAlchemyError:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=HealthResponse(
                status="degraded",
                service="homelab-monitor-api",
                version=__version__,
                database="down",
                timestamp=now,
            ).model_dump(mode="json"),
        )

    return HealthResponse(
        status="healthy",
        service="homelab-monitor-api",
        version=__version__,
        database="up",
        timestamp=now,
        photo_monitor=_photo_monitor_health(),
    )


def _photo_monitor_health() -> PhotoMonitorHealth:
    from homelab_monitor.photo_watcher import get_photo_watcher_service

    try:
        service = get_photo_watcher_service(get_settings())
    except Exception:
        return PhotoMonitorHealth(status="unknown")
    token = ""
    chat = ""
    try:
        token = service._settings.telegram_bot_token.get_secret_value().strip()
        chat = str(service._settings.telegram_chat_id or "").strip()
    except Exception:
        token = ""
    return PhotoMonitorHealth(
        status=service.self_check_status
        if service.self_check_status in {"pass", "fail"}
        else "unknown",
        running=service.last_successful_scan is not None or bool(service._primed),
        telegram_configured=bool(token and chat),
        pending=len(service._pending),
        last_telegram_at=service.last_successful_telegram,
        reasons=list(service.self_check_reasons),
    )

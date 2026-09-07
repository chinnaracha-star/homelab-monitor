from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from homelab_monitor import __version__
from homelab_monitor.database import get_db
from homelab_monitor.schemas import HealthResponse

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
    )

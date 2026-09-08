from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from homelab_monitor.auth.dependencies import require_roles
from homelab_monitor.database import get_db
from homelab_monitor.errors import APIError
from homelab_monitor.models import Notification
from homelab_monitor.notifications.config import (
    apply_updates,
    load_payload,
    public_settings,
    save_payload,
)
from homelab_monitor.notifications.dispatcher import retry_notification, send_test_notification
from homelab_monitor.schemas import (
    NotificationListResponse,
    NotificationResponse,
    NotificationSettingsResponse,
    NotificationSettingsUpdateRequest,
    NotificationTestRequest,
)
from homelab_monitor.settings import Settings, get_settings

router = APIRouter(prefix="/api/v1", tags=["notifications"])

READ = Depends(require_roles("admin", "operator", "viewer"))
SEND = Depends(require_roles("admin", "operator"))
CONFIGURE = Depends(require_roles("admin"))


def _public(row: Notification) -> NotificationResponse:
    response = NotificationResponse.model_validate(row)
    if response.channel in {"discord", "slack"}:
        return response.model_copy(update={"recipient": "configured webhook"})
    return response


def _to_update_dict(payload: NotificationSettingsUpdateRequest) -> dict:
    data: dict = {}
    for channel in ("telegram", "discord", "slack", "email"):
        section = getattr(payload, channel)
        if section is None:
            continue
        data[channel] = section.model_dump(exclude_unset=True)
    return data


@router.get(
    "/notifications",
    response_model=NotificationListResponse,
    dependencies=[READ],
    summary="List notification deliveries",
)
def list_notifications(
    db: Annotated[Session, Depends(get_db)],
    channel: Literal["telegram", "discord", "slack", "email"] | None = None,
    status: Literal["pending", "sent", "failed"] | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> NotificationListResponse:
    query = select(Notification)
    count_query = select(func.count(Notification.id))
    if channel:
        query = query.where(Notification.channel == channel)
        count_query = count_query.where(Notification.channel == channel)
    if status:
        query = query.where(Notification.status == status)
        count_query = count_query.where(Notification.status == status)
    total = int(db.scalar(count_query) or 0)
    rows = list(db.scalars(query.order_by(Notification.created_at.desc()).limit(limit)).all())
    return NotificationListResponse(
        total=total,
        notifications=[_public(row) for row in rows],
    )


@router.post(
    "/notifications/test",
    response_model=NotificationListResponse,
    dependencies=[SEND],
    summary="Send a test notification",
)
def test_notification(
    payload: NotificationTestRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> NotificationListResponse:
    rows = send_test_notification(db, settings, payload.channel)
    if not rows:
        raise APIError(
            400,
            "notification_channel_unconfigured",
            "No enabled notification channel is configured",
        )
    return NotificationListResponse(
        total=len(rows),
        notifications=[_public(row) for row in rows],
    )


@router.get(
    "/notifications/{notification_id}",
    response_model=NotificationResponse,
    dependencies=[READ],
    summary="Get one notification delivery",
)
def get_notification(
    notification_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> NotificationResponse:
    row = db.get(Notification, notification_id)
    if row is None:
        raise APIError(404, "notification_not_found", "The requested notification does not exist")
    return _public(row)


@router.post(
    "/notifications/{notification_id}/retry",
    response_model=NotificationResponse,
    dependencies=[SEND],
    summary="Retry a failed notification",
)
def retry_delivery(
    notification_id: str,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> NotificationResponse:
    row = db.get(Notification, notification_id)
    if row is None:
        raise APIError(404, "notification_not_found", "The requested notification does not exist")
    return _public(retry_notification(db, settings, row))


def _public_notification_settings(
    db: Session,
    settings: Settings,
    payload: dict | None = None,
) -> NotificationSettingsResponse:
    public = public_settings(settings, payload if payload is not None else load_payload(db))
    last_test = db.scalar(
        select(Notification.created_at)
        .where(Notification.channel == "telegram", Notification.alert_id.is_(None))
        .order_by(Notification.created_at.desc())
        .limit(1)
    )
    public["telegram"]["last_test"] = last_test
    return NotificationSettingsResponse.model_validate(public)


@router.get(
    "/settings/notifications",
    response_model=NotificationSettingsResponse,
    dependencies=[READ],
    summary="Get notification channel settings",
)
def get_notification_settings(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> NotificationSettingsResponse:
    return _public_notification_settings(db, settings)


@router.put(
    "/settings/notifications",
    response_model=NotificationSettingsResponse,
    dependencies=[CONFIGURE],
    summary="Update notification channel settings",
)
def update_notification_settings(
    payload: NotificationSettingsUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> NotificationSettingsResponse:
    stored = apply_updates(load_payload(db), _to_update_dict(payload))
    save_payload(db, stored)
    return _public_notification_settings(db, settings, stored)

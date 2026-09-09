from collections.abc import Callable
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from homelab_monitor.database import get_engine
from homelab_monitor.models import Notification
from homelab_monitor.notifications.config import load_payload, save_payload
from homelab_monitor.notifications.telegram import TelegramProvider
from homelab_monitor.settings import get_settings
from homelab_monitor.telegram_reports import (
    TelegramReportService,
    process_due_reports,
    reports_payload,
)


def _reset() -> None:
    with Session(get_engine()) as db:
        db.execute(delete(Notification))
        payload = load_payload(db)
        payload["reports"] = reports_payload({})
        payload.pop("telegram", None)
        save_payload(db, payload)


def _configure(db: Session, **report_updates: object) -> None:
    payload = load_payload(db)
    reports = reports_payload(payload)
    reports.update(report_updates)
    payload["reports"] = reports
    payload["telegram"] = {
        "enabled": True,
        "bot_token": "test-bot-token",
        "chat_id": "-1001",
    }
    save_payload(db, payload)


def test_reports_jwt_rbac_and_empty_settings(
    client: TestClient,
    auth_header: Callable[..., dict[str, str]],
) -> None:
    _reset()
    assert client.get("/api/v1/settings/notifications").status_code == 401
    body = client.get(
        "/api/v1/settings/notifications", headers=auth_header("viewer", "viewer123")
    ).json()
    assert body["reports"]["hourly_enabled"] is False
    assert body["reports"]["timezone"] == "Asia/Bangkok"
    denied = client.put(
        "/api/v1/settings/notifications",
        headers=auth_header("operator", "operator123"),
        json={"reports": {"hourly_enabled": True}},
    )
    assert denied.status_code == 403
    updated = client.put(
        "/api/v1/settings/notifications",
        headers=auth_header(),
        json={"reports": {"hourly_enabled": True, "timezone": "Asia/Bangkok"}},
    )
    assert updated.status_code == 200
    assert updated.json()["reports"]["hourly_enabled"] is True


def test_hourly_daily_weekly_generation_and_history(monkeypatch) -> None:
    _reset()
    sent: list[str] = []

    def fake_send(self: TelegramProvider, message: str) -> None:
        sent.append(message)

    monkeypatch.setattr(TelegramProvider, "send", fake_send)
    settings = get_settings()
    hourly_at = datetime(2026, 9, 8, 9, 0, tzinfo=UTC)
    with Session(get_engine()) as db:
        _configure(db, hourly_enabled=True)
        rows = process_due_reports(db, settings, now=hourly_at)
        assert len(rows) == 1
        assert rows[0].recipient == "hourly_report"
        assert rows[0].status == "sent"
        assert "HomeLab Hourly Report" in sent[-1]
        again = process_due_reports(db, settings, now=hourly_at)
        assert again == []
    daily_at = datetime(2026, 9, 8, 1, 5, tzinfo=UTC)
    with Session(get_engine()) as db:
        _configure(db, hourly_enabled=False, daily_enabled=True, timezone="Asia/Bangkok")
        rows = process_due_reports(db, settings, now=daily_at)
        assert len(rows) == 1
        assert rows[0].recipient == "daily_report"
        assert "HomeLab Daily Report" in sent[-1]
        assert "8 September 2026" in sent[-1]
    weekly_at = datetime(2026, 9, 6, 1, 5, tzinfo=UTC)
    with Session(get_engine()) as db:
        _configure(
            db,
            hourly_enabled=False,
            daily_enabled=False,
            weekly_enabled=True,
            timezone="Asia/Bangkok",
        )
        rows = process_due_reports(db, settings, now=weekly_at)
        assert len(rows) == 1
        assert rows[0].recipient == "weekly_report"
        assert "HomeLab Weekly Report" in sent[-1]
    with Session(get_engine()) as db:
        kinds = [
            row.recipient
            for row in db.scalars(select(Notification).order_by(Notification.created_at.asc()))
        ]
    assert kinds == ["hourly_report", "daily_report", "weekly_report"]


def test_disabled_reports_do_not_send(monkeypatch) -> None:
    _reset()
    sent: list[str] = []
    monkeypatch.setattr(TelegramProvider, "send", lambda self, message: sent.append(message))
    with Session(get_engine()) as db:
        _configure(db, hourly_enabled=False, daily_enabled=False, weekly_enabled=False)
        rows = process_due_reports(db, get_settings(), now=datetime(2026, 9, 6, 1, 5, tzinfo=UTC))
    assert rows == []
    assert sent == []


def test_skipped_failed_retry_and_timezone(
    monkeypatch,
    client: TestClient,
    auth_header: Callable[..., dict[str, str]],
) -> None:
    _reset()
    settings = get_settings()
    now = datetime(2026, 9, 8, 9, 0, tzinfo=UTC)
    with Session(get_engine()) as db:
        payload = load_payload(db)
        reports = reports_payload(payload)
        reports["hourly_enabled"] = True
        payload["reports"] = reports
        save_payload(db, payload)
        rows = process_due_reports(db, settings, now=now)
        assert rows[0].status == "skipped"
    sent: list[str] = []

    def fail_send(self: TelegramProvider, message: str) -> None:
        raise RuntimeError("telegram down")

    monkeypatch.setattr(TelegramProvider, "send", fail_send)
    fail_at = datetime(2026, 9, 8, 10, 0, tzinfo=UTC)
    with Session(get_engine()) as db:
        _configure(db, hourly_enabled=True)
        rows = process_due_reports(db, settings, now=fail_at)
        assert rows[0].status == "failed"
        failed_id = rows[0].id
    monkeypatch.setattr(TelegramProvider, "send", lambda self, message: sent.append(message))
    retried = client.post(
        f"/api/v1/notifications/{failed_id}/retry",
        headers=auth_header("operator", "operator123"),
    )
    assert retried.status_code == 200
    assert retried.json()["status"] == "sent"
    assert retried.json()["recipient"] == "hourly_report"
    assert "HomeLab Hourly Report" in sent[-1]
    bangkok = datetime(2026, 9, 8, 1, 5, tzinfo=UTC)
    with Session(get_engine()) as db:
        _configure(
            db,
            hourly_enabled=False,
            daily_enabled=True,
            timezone="UTC",
            daily_time="08:00",
        )
        utc_rows = process_due_reports(db, settings, now=bangkok)
        assert utc_rows == []
        _configure(
            db,
            hourly_enabled=False,
            daily_enabled=True,
            timezone="Asia/Bangkok",
            daily_time="08:00",
        )
        bangkok_rows = process_due_reports(db, settings, now=bangkok)
        assert len(bangkok_rows) == 1
        assert bangkok_rows[0].recipient == "daily_report"


def test_manual_test_report_jwt_rbac_disabled_success_retry_and_history(
    client: TestClient,
    auth_header: Callable[..., dict[str, str]],
    monkeypatch,
) -> None:
    _reset()
    assert client.post("/api/v1/notifications/test-report").status_code == 401
    viewer = client.post(
        "/api/v1/notifications/test-report",
        headers=auth_header("viewer", "viewer123"),
    )
    operator = client.post(
        "/api/v1/notifications/test-report",
        headers=auth_header("operator", "operator123"),
    )
    assert viewer.status_code == 403
    assert operator.status_code == 403
    missing = client.post("/api/v1/notifications/test-report", headers=auth_header())
    assert missing.status_code == 409
    assert missing.json() == {"status": "telegram_not_configured"}
    sent: list[str] = []
    monkeypatch.setattr(TelegramProvider, "send", lambda self, message: sent.append(message))
    with Session(get_engine()) as db:
        _configure(db)
        now = datetime(2026, 9, 8, 9, 42, 18, tzinfo=UTC)
        body = TelegramReportService().build_test_report(db, now=now)
    assert "HomeLab Test Report" in body
    assert "Telegram connection successful" in body
    assert "8 September 2026" in body
    assert "16:42:18" in body
    assert "Settings → Send Test Report" in body
    posted = client.post("/api/v1/notifications/test-report", headers=auth_header())
    assert posted.status_code == 200
    payload = posted.json()
    assert payload["status"] == "sent"
    assert payload["provider"] == "telegram"
    assert payload["notification_id"]
    assert "HomeLab Test Report" in sent[-1]
    history = client.get(
        "/api/v1/notifications/history",
        headers=auth_header("viewer", "viewer123"),
    )
    titles = [item["title"] for item in history.json()["items"]]
    assert "Test Report" in titles

    def fail_send(self: TelegramProvider, message: str) -> None:
        raise RuntimeError("telegram down")

    monkeypatch.setattr(TelegramProvider, "send", fail_send)
    failed = client.post("/api/v1/notifications/test-report", headers=auth_header())
    assert failed.status_code == 200
    assert failed.json()["status"] == "failed"
    failed_id = failed.json()["notification_id"]
    sent.clear()
    monkeypatch.setattr(TelegramProvider, "send", lambda self, message: sent.append(message))
    retried = client.post(
        f"/api/v1/notifications/{failed_id}/retry",
        headers=auth_header("operator", "operator123"),
    )
    assert retried.status_code == 200
    assert retried.json()["status"] == "sent"
    assert retried.json()["recipient"] == "test_report"
    assert "HomeLab Test Report" in sent[-1]

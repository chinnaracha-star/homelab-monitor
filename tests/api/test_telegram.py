from datetime import UTC, datetime

import httpx
import pytest
from fastapi.testclient import TestClient

from homelab_monitor.alert_engine import AlertEvent
from homelab_monitor.settings import Settings
from homelab_monitor.telegram import (
    TelegramNotificationError,
    TelegramNotifier,
    dispatch_alert_events,
    format_alert_message,
    format_telegram_test_message,
    telegram_config_error,
)

REGISTRATION_KEY = "test-registration-key-at-least-24-chars"


def make_event(kind: str) -> AlertEvent:
    return AlertEvent(
        agent_id="agent-id",
        agent_name="home-srv-01",
        kind=kind,
        resource="system",
        value=95,
        threshold=90,
        message="Metric 95 exceeded threshold 90",
        observed_at=datetime(2026, 9, 7, 9, 0, tzinfo=UTC),
    )


def test_notifier_uses_configured_url_and_telegram_payload() -> None:
    captured: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured
        captured = request
        return httpx.Response(200, json={"ok": True, "result": {}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    notifier = TelegramNotifier(
        api_base_url="https://telegram.example.test",
        bot_token="test-bot-token",
        chat_id="-100123",
        timeout=5,
        client=client,
    )

    notifier.send_alert(make_event("cpu_high"))

    assert captured is not None
    assert str(captured.url) == ("https://telegram.example.test/bottest-bot-token/sendMessage")
    body = captured.read().decode()
    assert '"chat_id":"-100123"' in body
    assert "CPU Warning" in body
    assert "home-srv-01" in body


@pytest.mark.parametrize(
    ("kind", "title"),
    [
        ("agent_offline", "Agent Offline"),
        ("cpu_high", "CPU Warning"),
        ("memory_high", "Memory Warning"),
        ("disk_high", "Disk Warning"),
        ("temperature_high", "Temperature Warning"),
    ],
)
def test_supported_alert_messages(kind: str, title: str) -> None:
    message = format_alert_message(make_event(kind))

    assert title in message
    assert "Agent: home-srv-01" in message


def test_dispatch_is_disabled_without_credentials() -> None:
    settings = Settings(
        registration_key=REGISTRATION_KEY,
        telegram_api_base_url="https://telegram.example.test",
        telegram_bot_token=None,
        telegram_chat_id=None,
    )

    dispatch_alert_events(settings, [make_event("cpu_high")])


def test_report_upload_notifies_only_on_alert_transition(
    client: TestClient,
    monkeypatch,
) -> None:
    event_batches: list[list[AlertEvent]] = []

    def capture_events(_settings: Settings, events: list[AlertEvent]) -> None:
        event_batches.append(events)

    monkeypatch.setattr(
        "homelab_monitor.routers.agents.dispatch_alert_events",
        capture_events,
    )
    registration = client.post(
        "/api/v1/agents/register",
        headers={"X-Registration-Key": REGISTRATION_KEY},
        json={
            "name": "telegram-agent",
            "hostname": "telegram-agent.local",
            "version": "0.1.0",
            "capabilities": ["ubuntu"],
        },
    ).json()

    def upload(report_id: str) -> None:
        response = client.post(
            "/api/v1/agent/reports",
            headers={"Authorization": f"Bearer {registration['agent_token']}"},
            json={
                "report_id": report_id,
                "schema_version": "1.0",
                "observed_at": datetime.now(UTC).isoformat(),
                "config_revision": 1,
                "modules": [
                    {
                        "module": "system",
                        "status": "warning",
                        "summary": "CPU threshold exceeded",
                        "metrics": {"cpu": {"usage_percent": 95}},
                        "diagnostics": {},
                    }
                ],
            },
        )
        assert response.status_code == 200

    upload("telegram-alert-001")
    upload("telegram-alert-002")

    assert len(event_batches) == 1
    assert [event.kind for event in event_batches[0]] == ["cpu_high"]


def test_telegram_test_message_includes_required_fields() -> None:
    message = format_telegram_test_message(
        server="production",
        version="8.3.5",
        observed_at=datetime(2026, 9, 8, 2, 0, tzinfo=UTC),
    )
    assert message.startswith("🚀 Homelab Monitor Test")
    assert "Time: 2026-09-08T02:00:00+00:00" in message
    assert "Server: production" in message
    assert "Version: 8.3.5" in message
    assert "Status: ok" in message


def test_telegram_config_error_names_missing_fields() -> None:
    assert "bot token" in telegram_config_error("https://api.telegram.org", "", "-100")
    assert "chat ID" in telegram_config_error("https://api.telegram.org", "token", "")


def _notifier(handler) -> TelegramNotifier:
    return TelegramNotifier(
        api_base_url="https://telegram.example.test",
        bot_token="123456:AAHsecretTokenValue",
        chat_id="-100123",
        timeout=2,
        client=httpx.Client(transport=httpx.MockTransport(handler), timeout=2),
    )


def test_verify_connection_calls_get_me() -> None:
    captured: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured
        captured = request
        return httpx.Response(200, json={"ok": True, "result": {"id": 1}})

    notifier = _notifier(handler)
    me = notifier.verify_connection()
    assert captured is not None
    assert captured.method == "GET"
    assert str(captured.url).endswith("/bot123456:AAHsecretTokenValue/getMe")
    assert notifier.last_http_status == 200
    assert me["result"]["id"] == 1
    notifier.close()


def test_invalid_token_and_chat_id_errors() -> None:
    def unauthorized(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={"ok": False, "error_code": 401, "description": "Unauthorized"},
        )

    notifier = _notifier(unauthorized)
    with pytest.raises(TelegramNotificationError, match="bot token"):
        notifier.send_text("hello")
    notifier.close()

    def missing_chat(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"ok": False, "error_code": 400, "description": "Bad Request: chat not found"},
        )

    notifier = _notifier(missing_chat)
    with pytest.raises(TelegramNotificationError, match="chat ID"):
        notifier.send_text("hello")
    notifier.close()


def test_http_error_redacts_bot_token() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "ok": False,
                "description": "failed for 123456:AAHsecretTokenValue",
            },
        )

    notifier = _notifier(handler)
    with pytest.raises(TelegramNotificationError) as error:
        notifier.send_text("hello")
    assert "AAHsecretTokenValue" not in str(error.value)
    notifier.close()


def test_http_429_retries_after_retry_after() -> None:
    attempts = {"count": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return httpx.Response(
                429,
                json={
                    "ok": False,
                    "error_code": 429,
                    "description": "Too Many Requests: retry after 1",
                    "parameters": {"retry_after": 0},
                },
            )
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 9}})

    notifier = _notifier(handler)
    body = notifier.send_text("hello")
    assert attempts["count"] == 2
    assert notifier.last_http_status == 200
    assert body["result"]["message_id"] == 9
    notifier.close()


def test_network_failure_is_telegram_error() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    notifier = _notifier(handler)
    with pytest.raises(TelegramNotificationError, match="network failure"):
        notifier.send_text("hello")
    notifier.close()
    notifier.close()

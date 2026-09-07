from collections.abc import Callable

from fastapi.testclient import TestClient
from httpx import Response

from homelab_monitor.auth.dependencies import PERMISSION_DENIED_MESSAGE

REGISTRATION_KEY = "test-registration-key-at-least-24-chars"


def _permission_denied(response: Response) -> None:
    assert response.status_code == 403
    error = response.json()["error"]
    assert error["code"] == "permission_denied"
    assert error["message"] == PERMISSION_DENIED_MESSAGE


def test_all_roles_can_read_dashboard_and_alerts(
    client: TestClient,
    auth_header: Callable[..., dict[str, str]],
) -> None:
    for username, password in (
        ("admin", "admin123"),
        ("operator", "operator123"),
        ("viewer", "viewer123"),
    ):
        headers = auth_header(username, password)
        overview = client.get("/api/v1/dashboard/overview", headers=headers)
        alerts = client.get("/api/v1/alerts/active", headers=headers)
        assert overview.status_code == 200
        assert alerts.status_code == 200


def test_admin_is_allowed_to_list_users(
    client: TestClient,
    auth_header: Callable[..., dict[str, str]],
) -> None:
    response = client.get("/api/v1/users", headers=auth_header("admin", "admin123"))
    assert response.status_code == 200
    usernames = [user["username"] for user in response.json()]
    assert usernames == sorted(usernames)
    assert {"admin", "operator", "viewer", "disabled"}.issubset(set(usernames))
    assert all("password_hash" not in user for user in response.json())


def test_operator_and_viewer_are_denied_user_management(
    client: TestClient,
    auth_header: Callable[..., dict[str, str]],
) -> None:
    _permission_denied(client.get("/api/v1/users", headers=auth_header("operator", "operator123")))
    _permission_denied(client.get("/api/v1/users", headers=auth_header("viewer", "viewer123")))


def test_viewer_cannot_acknowledge_alerts(
    client: TestClient,
    auth_header: Callable[..., dict[str, str]],
) -> None:
    _permission_denied(
        client.post(
            "/api/v1/alerts/missing-alert/acknowledge",
            headers=auth_header("viewer", "viewer123"),
        )
    )


def test_operator_and_admin_can_acknowledge_alerts(
    client: TestClient,
    auth_header: Callable[..., dict[str, str]],
) -> None:
    register = client.post(
        "/api/v1/agents/register",
        headers={"X-Registration-Key": REGISTRATION_KEY},
        json={
            "name": "rbac-alert-agent",
            "hostname": "rbac-alert-agent.local",
            "version": "0.1.0",
            "capabilities": ["ubuntu"],
        },
    )
    assert register.status_code == 201
    token = register.json()["agent_token"]
    report = client.post(
        "/api/v1/agent/reports",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "report_id": "rbac-alert-report",
            "schema_version": "1.0",
            "observed_at": "2026-09-07T09:00:00Z",
            "config_revision": 1,
            "modules": [
                {
                    "module": "system",
                    "status": "warning",
                    "summary": "CPU is high",
                    "metrics": {"cpu": {"usage_percent": 100.0}},
                    "diagnostics": {},
                }
            ],
        },
    )
    assert report.status_code == 200
    alerts = client.get(
        "/api/v1/alerts/active",
        headers=auth_header("operator", "operator123"),
    )
    assert alerts.status_code == 200
    alert_id = next(item["id"] for item in alerts.json() if item["kind"] == "cpu_high")

    operator = client.post(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        headers=auth_header("operator", "operator123"),
    )
    admin = client.post(
        f"/api/v1/alerts/{alert_id}/acknowledge",
        headers=auth_header("admin", "admin123"),
    )
    assert operator.status_code == 200
    assert admin.status_code == 200
    assert operator.json()["id"] == alert_id
    assert operator.json()["status"] == "active"

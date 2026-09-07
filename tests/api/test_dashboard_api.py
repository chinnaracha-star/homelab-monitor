from fastapi.testclient import TestClient

from homelab_monitor.settings import get_settings

REGISTRATION_KEY = "test-registration-key-at-least-24-chars"


def register_agent(
    client: TestClient,
    name: str,
    capabilities: list[str] | None = None,
) -> tuple[str, str]:
    response = client.post(
        "/api/v1/agents/register",
        headers={"X-Registration-Key": REGISTRATION_KEY},
        json={
            "name": name,
            "hostname": f"{name}.local",
            "version": "0.1.0",
            "capabilities": capabilities or ["ubuntu"],
        },
    )
    assert response.status_code == 201
    body = response.json()
    return body["agent_id"], body["agent_token"]


def upload_report(
    client: TestClient,
    token: str,
    report_id: str,
    observed_at: str,
    cpu_percent: float,
) -> None:
    response = client.post(
        "/api/v1/agent/reports",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "report_id": report_id,
            "schema_version": "1.0",
            "observed_at": observed_at,
            "config_revision": 1,
            "modules": [
                {
                    "module": "system",
                    "status": "healthy",
                    "summary": "System operating normally",
                    "metrics": {"cpu": {"usage_percent": cpu_percent}},
                    "diagnostics": {},
                }
            ],
        },
    )
    assert response.status_code == 200


def test_dashboard_overview_and_agent_list(client: TestClient) -> None:
    online_id, online_token = register_agent(client, "dashboard-online")
    register_agent(client, "dashboard-offline")
    check_in = client.post(
        "/api/v1/agent/check-ins",
        headers={"Authorization": f"Bearer {online_token}"},
        json={
            "version": "0.1.0",
            "observed_at": "2026-09-07T06:00:00Z",
            "config_revision": 1,
        },
    )
    assert check_in.status_code == 200

    agents_response = client.get("/api/v1/agents")
    overview_response = client.get("/api/v1/dashboard/overview")

    assert agents_response.status_code == 200
    assert overview_response.status_code == 200
    agents = agents_response.json()
    overview = overview_response.json()
    assert [agent["name"] for agent in agents] == sorted(agent["name"] for agent in agents)
    assert overview["agents"]["total"] == len(agents)
    assert overview["agents"]["online"] == sum(agent["status"] == "online" for agent in agents)
    assert overview["agents"]["offline"] == (
        overview["agents"]["total"] - overview["agents"]["online"]
    )
    assert isinstance(overview["reports"]["total"], int)

    listed_agent = next(agent for agent in agents if agent["id"] == online_id)
    assert set(listed_agent) == {
        "id",
        "name",
        "hostname",
        "version",
        "status",
        "last_seen_at",
    }


def test_agent_detail_returns_configuration_and_capabilities(client: TestClient) -> None:
    agent_id, _ = register_agent(
        client,
        "dashboard-detail",
        capabilities=["ubuntu", "docker"],
    )

    response = client.get(f"/api/v1/agents/{agent_id}")

    assert response.status_code == 200
    assert response.json() == {
        "id": agent_id,
        "name": "dashboard-detail",
        "hostname": "dashboard-detail.local",
        "version": "0.1.0",
        "status": "registered",
        "last_seen_at": None,
        "configuration_revision": 1,
        "capabilities": ["docker", "ubuntu"],
    }


def test_latest_report_uses_observation_time(client: TestClient) -> None:
    agent_id, token = register_agent(client, "dashboard-reports")
    upload_report(
        client,
        token,
        "dashboard-newer-report",
        "2026-09-07T07:00:00Z",
        20.0,
    )
    upload_report(
        client,
        token,
        "dashboard-older-report",
        "2026-09-07T06:00:00Z",
        10.0,
    )

    response = client.get(f"/api/v1/agents/{agent_id}/latest-report")

    assert response.status_code == 200
    assert response.json()["agent_id"] == agent_id
    assert response.json()["report_id"] == "dashboard-newer-report"
    assert response.json()["payload"]["modules"][0]["metrics"]["cpu"]["usage_percent"] == 20.0


def test_dashboard_agent_not_found_responses(client: TestClient) -> None:
    detail = client.get("/api/v1/agents/missing-agent")
    latest = client.get("/api/v1/agents/missing-agent/latest-report")

    assert detail.status_code == 404
    assert detail.json()["error"]["code"] == "agent_not_found"
    assert latest.status_code == 404
    assert latest.json()["error"]["code"] == "agent_not_found"


def test_latest_report_not_found_for_registered_agent(client: TestClient) -> None:
    agent_id, _ = register_agent(client, "dashboard-no-reports")

    response = client.get(f"/api/v1/agents/{agent_id}/latest-report")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "latest_report_not_found"


def test_dashboard_routes_are_documented_in_openapi(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/dashboard/overview" in paths
    assert "/api/v1/agents" in paths
    assert "/api/v1/agents/{agent_id}" in paths
    assert "/api/v1/agents/{agent_id}/latest-report" in paths
    assert "/api/v1/agents/{agent_id}/reports" in paths
    assert "/api/v1/alerts/active" in paths


def test_agent_report_history_returns_newest_reports_first(client: TestClient) -> None:
    agent_id, token = register_agent(client, "dashboard-history")
    upload_report(
        client,
        token,
        "history-oldest",
        "2026-09-07T05:00:00Z",
        10.0,
    )
    upload_report(
        client,
        token,
        "history-newest",
        "2026-09-07T07:00:00Z",
        30.0,
    )
    upload_report(
        client,
        token,
        "history-middle",
        "2026-09-07T06:00:00Z",
        20.0,
    )

    response = client.get(f"/api/v1/agents/{agent_id}/reports", params={"limit": 2})

    assert response.status_code == 200
    assert [report["report_id"] for report in response.json()] == [
        "history-newest",
        "history-middle",
    ]


def test_agent_report_history_validates_agent_and_limit(client: TestClient) -> None:
    missing = client.get("/api/v1/agents/missing-agent/reports")
    invalid_limit = client.get("/api/v1/agents/missing-agent/reports", params={"limit": 1})

    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "agent_not_found"
    assert invalid_limit.status_code == 422


def test_active_alerts_include_agent_context(client: TestClient) -> None:
    agent_id, token = register_agent(client, "dashboard-active-alert")
    upload_report(
        client,
        token,
        "dashboard-alert-report",
        "2026-09-07T08:00:00Z",
        100.0,
    )

    response = client.get("/api/v1/alerts/active")

    assert response.status_code == 200
    alert = next(item for item in response.json() if item["agent_id"] == agent_id)
    assert alert["agent_name"] == "dashboard-active-alert"
    assert alert["kind"] == "cpu_high"
    assert alert["severity"] == "warning"
    assert alert["current_value"] == 100
    assert alert["threshold"] == get_settings().alert_cpu_threshold_percent

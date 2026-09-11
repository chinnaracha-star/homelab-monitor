from homelab_monitor.schemas import RemoteAccessResponse
from homelab_monitor.settings import get_settings
from homelab_monitor.telegram_links import is_telegram_button_url, resolve_dashboard_url


def test_dashboard_url_prefers_configured_then_tailnet(monkeypatch) -> None:
    settings = get_settings().model_copy(
        update={"dashboard_health_url": "https://dash.example/", "dashboard_port": 18081}
    )
    assert resolve_dashboard_url(settings) == "https://dash.example"

    settings = get_settings().model_copy(
        update={"dashboard_health_url": "http://dashboard:8080/", "dashboard_port": 18081}
    )
    monkeypatch.setattr(
        "homelab_monitor.telegram_links.RemoteAccessService.snapshot",
        lambda self: RemoteAccessResponse(
            hostname="home-srv-01.tail1ea57f.ts.net",
            https=True,
        ),
    )
    assert resolve_dashboard_url(settings) == "https://home-srv-01.tail1ea57f.ts.net"

    monkeypatch.setattr(
        "homelab_monitor.telegram_links.RemoteAccessService.snapshot",
        lambda self: RemoteAccessResponse(),
    )
    assert resolve_dashboard_url(settings) is None
    assert not is_telegram_button_url("http://dashboard:8080")
    assert not is_telegram_button_url("http://127.0.0.1:18081")

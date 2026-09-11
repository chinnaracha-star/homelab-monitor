from homelab_monitor.schemas import RemoteAccessResponse
from homelab_monitor.settings import get_settings
from homelab_monitor.telegram_links import resolve_dashboard_url


def test_dashboard_url_prefers_configured_then_tailnet_then_localhost(monkeypatch) -> None:
    settings = get_settings().model_copy(
        update={"dashboard_health_url": "https://dash.example/", "dashboard_port": 18081}
    )
    assert resolve_dashboard_url(settings) == "https://dash.example"

    settings = get_settings().model_copy(
        update={"dashboard_health_url": "", "dashboard_port": 18081}
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
    assert resolve_dashboard_url(settings) == "http://127.0.0.1:18081"

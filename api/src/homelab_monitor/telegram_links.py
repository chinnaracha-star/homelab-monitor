from __future__ import annotations

from contextvars import ContextVar, Token
from urllib.parse import urlparse

from fastapi import Request

from homelab_monitor.remote_access import RemoteAccessService
from homelab_monitor.settings import Settings, get_settings

_request_origin: ContextVar[str | None] = ContextVar("telegram_request_origin", default=None)


def bind_request_origin(request: Request) -> Token:
    return _request_origin.set(_origin_from_request(request))


def reset_request_origin(token: Token) -> None:
    _request_origin.reset(token)


def _origin_from_request(request: Request) -> str | None:
    forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if not forwarded_host:
        return None
    host = forwarded_host.split(",", 1)[0].strip()
    if not host:
        return None
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "http").split(",")[0]
    return f"{proto.strip()}://{host}".rstrip("/")


def _clean_url(value: str | None) -> str | None:
    text = (value or "").strip().rstrip("/")
    if not text:
        return None
    parsed = urlparse(text if "://" in text else f"https://{text}")
    if not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/") or None


def _tailnet_url(settings: Settings) -> str | None:
    access = RemoteAccessService(settings=settings).snapshot()
    hostname = (access.hostname or "").strip().rstrip(".")
    if not hostname:
        return None
    return f"https://{hostname}"


def _localhost_url(settings: Settings) -> str:
    return f"http://127.0.0.1:{settings.dashboard_port}"


def resolve_dashboard_url(settings: Settings | None = None) -> str | None:
    config = settings or get_settings()
    configured = _clean_url(config.dashboard_health_url)
    if configured:
        return configured
    current = _clean_url(_request_origin.get())
    if current:
        return current
    tailnet = _clean_url(_tailnet_url(config))
    if tailnet:
        return tailnet
    return _clean_url(_localhost_url(config))


def resolve_immich_url(settings: Settings | None = None) -> str | None:
    config = settings or get_settings()
    return _clean_url(config.immich_url)


def resolve_qnap_url(settings: Settings | None = None) -> str | None:
    config = settings or get_settings()
    return _clean_url(config.qnap_url)

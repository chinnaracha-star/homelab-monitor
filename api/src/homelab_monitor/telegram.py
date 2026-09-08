import re
import socket
import time
from datetime import UTC, datetime

import httpx

from homelab_monitor import __version__
from homelab_monitor.alert_engine import AlertEvent
from homelab_monitor.settings import Settings

ALERT_TITLES = {
    "agent_offline": "Agent Offline",
    "cpu_high": "CPU Warning",
    "memory_high": "Memory Warning",
    "disk_high": "Disk Warning",
    "temperature_high": "Temperature Warning",
}

_TOKEN_PATTERN = re.compile(r"\d+:[A-Za-z0-9_-]+")
DEFAULT_TELEGRAM_API_BASE_URL = "https://api.telegram.org"


class TelegramNotificationError(Exception):
    """Telegram rejected a notification or could not be reached."""


class TelegramNotifier:
    def __init__(
        self,
        *,
        api_base_url: str,
        bot_token: str,
        chat_id: str,
        timeout: float,
        client: httpx.Client | None = None,
    ) -> None:
        missing = []
        if not api_base_url:
            missing.append("API base URL")
        if not bot_token:
            missing.append("bot token")
        if not chat_id:
            missing.append("chat ID")
        if missing:
            raise ValueError("Telegram " + ", ".join(missing) + " must be configured")
        self._api_base_url = api_base_url.rstrip("/")
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout)
        self.last_http_status = 0

    @property
    def recipient(self) -> str:
        return self._chat_id

    def _method_url(self, method: str) -> str:
        return f"{self._api_base_url}/bot{self._bot_token}/{method}"

    @classmethod
    def from_settings(cls, settings: Settings) -> "TelegramNotifier | None":
        token = (
            settings.telegram_bot_token.get_secret_value() if settings.telegram_bot_token else ""
        )
        chat_id = settings.telegram_chat_id or ""
        api_base_url = settings.telegram_api_base_url or DEFAULT_TELEGRAM_API_BASE_URL
        if not token and not chat_id:
            return None
        if not api_base_url or not token or not chat_id:
            raise ValueError(telegram_config_error(api_base_url, token, chat_id))
        return cls(
            api_base_url=api_base_url,
            bot_token=token,
            chat_id=chat_id,
            timeout=settings.telegram_request_timeout,
        )

    def verify_connection(self) -> dict:
        return self._request("GET", "getMe")

    def _request(self, method: str, api_method: str, json: dict | None = None) -> dict:
        kwargs: dict = {}
        if json is not None:
            kwargs["json"] = json
        response = self._send(method, api_method, kwargs)
        for _attempt in range(2):
            if response.status_code != 429:
                break
            time.sleep(_retry_after_seconds(response))
            response = self._send(method, api_method, kwargs)
        return _parse_telegram_response(response)

    def _send(self, method: str, api_method: str, kwargs: dict) -> httpx.Response:
        self.last_http_status = 0
        try:
            response = self._client.request(method, self._method_url(api_method), **kwargs)
        except httpx.TimeoutException as error:
            raise TelegramNotificationError("Telegram request timed out") from error
        except httpx.RequestError as error:
            raise TelegramNotificationError("Telegram network failure") from error
        self.last_http_status = response.status_code
        return response

    def send_text(self, text: str) -> dict:
        return self._request("POST", "sendMessage", json={"chat_id": self._chat_id, "text": text})

    def send_alert(self, event: AlertEvent) -> None:
        self.send_text(format_alert_message(event))

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


def telegram_config_error(api_base_url: str, bot_token: str, chat_id: str) -> str:
    missing: list[str] = []
    if not api_base_url:
        missing.append("API base URL")
    if not bot_token:
        missing.append("bot token")
    if not chat_id:
        missing.append("chat ID")
    if not missing:
        return "Telegram configuration is invalid"
    if len(missing) == 1:
        return f"Telegram {missing[0]} must be configured"
    if len(missing) == 2:
        return f"Telegram {missing[0]} and {missing[1]} must be configured"
    return "Telegram API base URL, bot token, and chat ID must be configured together"


def format_telegram_test_message(
    *,
    server: str | None = None,
    version: str | None = None,
    observed_at: datetime | None = None,
) -> str:
    stamp = (observed_at or datetime.now(UTC)).isoformat()
    return "\n".join(
        (
            "🚀 Homelab Monitor Test",
            f"Time: {stamp}",
            f"Server: {server or socket.gethostname()}",
            f"Version: {version or __version__}",
            "Status: ok",
        )
    )


def format_alert_message(event: AlertEvent) -> str:
    title = ALERT_TITLES.get(event.kind, "HomeLab Warning")
    return "\n".join(
        (
            f"HomeLab Monitor: {title}",
            f"Agent: {event.agent_name}",
            f"Resource: {event.resource}",
            event.message,
            f"Observed: {event.observed_at.isoformat()}",
        )
    )


def dispatch_alert_events(
    settings: Settings,
    events: list[AlertEvent],
    notifier: TelegramNotifier | None = None,
) -> None:
    from homelab_monitor.notifications.dispatcher import dispatch_alert_notifications

    dispatch_alert_notifications(settings, events, telegram_notifier=notifier)


def _parse_telegram_response(response: httpx.Response) -> dict:
    try:
        body = response.json()
    except ValueError:
        body = {}
    description = redact_telegram_secrets(str(body.get("description") or ""))
    error_code = body.get("error_code")
    lowered = description.lower()
    if response.status_code in {401, 403} or error_code in {401, 403} or "unauthorized" in lowered:
        raise TelegramNotificationError("Telegram rejected the bot token")
    if "chat not found" in lowered or "chat_id is empty" in lowered:
        raise TelegramNotificationError("Telegram rejected the chat ID")
    if response.status_code >= 400:
        detail = f": {description}" if description else ""
        raise TelegramNotificationError(
            f"Telegram Bot API returned HTTP {response.status_code}{detail}"
        )
    if body.get("ok") is not True:
        raise TelegramNotificationError(description or "Telegram Bot API rejected the message")
    return body if isinstance(body, dict) else {}


def redact_telegram_secrets(text: str) -> str:
    return _TOKEN_PATTERN.sub("[redacted]", text)


def _retry_after_seconds(response: httpx.Response) -> float:
    header = response.headers.get("Retry-After")
    if header:
        try:
            return min(max(float(header), 1), 30)
        except ValueError:
            pass
    try:
        body = response.json()
    except ValueError:
        body = {}
    wait = None
    if isinstance(body, dict):
        parameters = body.get("parameters")
        if isinstance(parameters, dict):
            wait = parameters.get("retry_after")
    try:
        return min(max(float(wait or 2), 1), 30)
    except (TypeError, ValueError):
        return 2.0

import logging

import httpx

from homelab_monitor.alert_engine import AlertEvent
from homelab_monitor.settings import Settings

logger = logging.getLogger("homelab_monitor.telegram")

ALERT_TITLES = {
    "agent_offline": "Agent Offline",
    "cpu_high": "CPU Warning",
    "memory_high": "Memory Warning",
    "disk_high": "Disk Warning",
    "temperature_high": "Temperature Warning",
}


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
        if not api_base_url or not bot_token or not chat_id:
            raise ValueError("Telegram API URL, bot token, and chat ID are required")
        self._endpoint = f"{api_base_url.rstrip('/')}/bot{bot_token}/sendMessage"
        self._chat_id = chat_id
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=timeout)

    @classmethod
    def from_settings(cls, settings: Settings) -> "TelegramNotifier | None":
        token = (
            settings.telegram_bot_token.get_secret_value() if settings.telegram_bot_token else ""
        )
        chat_id = settings.telegram_chat_id or ""
        if not token and not chat_id:
            return None
        if not settings.telegram_api_base_url or not token or not chat_id:
            raise ValueError(
                "TELEGRAM_API_BASE_URL, TELEGRAM_BOT_TOKEN, and TELEGRAM_CHAT_ID "
                "must be configured together"
            )
        return cls(
            api_base_url=settings.telegram_api_base_url,
            bot_token=token,
            chat_id=chat_id,
            timeout=settings.telegram_request_timeout,
        )

    def send_alert(self, event: AlertEvent) -> None:
        response = self._client.post(
            self._endpoint,
            json={
                "chat_id": self._chat_id,
                "text": format_alert_message(event),
            },
        )
        if response.status_code >= 400:
            raise TelegramNotificationError(
                f"Telegram Bot API returned HTTP {response.status_code}"
            )
        body = response.json()
        if body.get("ok") is not True:
            raise TelegramNotificationError("Telegram Bot API rejected the message")

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


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
    if not events:
        return

    owns_notifier = notifier is None
    try:
        active_notifier = notifier or TelegramNotifier.from_settings(settings)
    except ValueError as error:
        logger.error("telegram_configuration_invalid", extra={"reason": str(error)})
        return
    if active_notifier is None:
        logger.info("telegram_notifications_disabled")
        return

    try:
        for event in events:
            try:
                active_notifier.send_alert(event)
            except (httpx.HTTPError, TelegramNotificationError, ValueError):
                logger.exception(
                    "telegram_notification_failed",
                    extra={
                        "agent_id": event.agent_id,
                        "kind": event.kind,
                        "resource": event.resource,
                    },
                )
            else:
                logger.info(
                    "telegram_notification_sent",
                    extra={
                        "agent_id": event.agent_id,
                        "kind": event.kind,
                        "resource": event.resource,
                    },
                )
    finally:
        if owns_notifier:
            active_notifier.close()

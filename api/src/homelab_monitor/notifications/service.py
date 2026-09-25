"""Facade over the existing Telegram notifier.

SQLite backup text and scheduled report delivery use this facade. The
notification worker and Photo Monitor still call TelegramNotifier directly.
Report retry and history stay in the dispatcher.
"""

from homelab_monitor.settings import Settings
from homelab_monitor.telegram import TelegramNotifier


class NotificationService:
    """Delegates text delivery to the current Telegram implementation."""

    def __init__(self, notifier: TelegramNotifier) -> None:
        self._notifier = notifier

    @classmethod
    def from_settings(cls, settings: Settings) -> "NotificationService | None":
        notifier = TelegramNotifier.from_settings(settings)
        if notifier is None:
            return None
        return cls(notifier)

    def send_text(self, text: str) -> dict:
        return self._notifier.send_text(text)

    def close(self) -> None:
        self._notifier.close()

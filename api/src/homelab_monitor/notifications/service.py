"""Facade over the existing Telegram notifier.

SQLite backup text, scheduled report delivery, and the notification worker
use this facade. Photo Monitor still calls TelegramNotifier directly.
Retry and history stay with the dispatcher and the worker.
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

    @property
    def recipient(self) -> str:
        return self._notifier.recipient

    def send_text(self, text: str) -> dict:
        return self._notifier.send_text(text)

    def close(self) -> None:
        self._notifier.close()

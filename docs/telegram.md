# Telegram notifications

HomeLab Monitor can send alert transitions through the Telegram Bot API. The
notifier supports agent-offline, CPU, memory, disk, and temperature warnings.
Repeated observations of an already-active alert do not send duplicate messages.

## Configuration

Create a bot with BotFather, identify the destination chat, and configure `.env`:

```env
TELEGRAM_API_BASE_URL=https://api.telegram.org
TELEGRAM_BOT_TOKEN=replace-with-the-bot-token
TELEGRAM_CHAT_ID=replace-with-the-chat-id
TELEGRAM_REQUEST_TIMEOUT=10
```

The Bot API base URL is configurable and is not embedded in the notifier.
`TELEGRAM_BOT_TOKEN` is loaded as a secret value. HTTP client logging is held at
warning level so the token-bearing Telegram request path is never written to
normal application logs.

Leave both `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` empty to disable delivery.
If only one is configured, the server records a configuration error without
failing agent report ingestion.

## Delivery behavior

Metric alerts are queued as FastAPI background tasks after alert state commits.
Offline-agent alerts are sent after the periodic liveness transaction commits.
Telegram failures are logged and do not roll back reports or alert state.

Notification delivery is reusable through `TelegramNotifier.send_alert()` and
`dispatch_alert_events()`. Tests replace the HTTP transport and never contact
the public Telegram service.

Recovery notifications and a durable notification outbox are not implemented
yet.

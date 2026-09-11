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
TELEGRAM_REQUEST_TIMEOUT=30
HOMELAB_TELEGRAM_ENABLED=true
```

`HOMELAB_TELEGRAM_ENABLED` defaults to **true** in Settings, Compose, and env
examples so production does not silently disable Telegram. Delivery still no-ops
when the bot token or chat ID is empty.

The Bot API base URL is configurable and is not embedded in the notifier.
`TELEGRAM_BOT_TOKEN` is loaded as a secret value. HTTP client logging is held at
warning level so the token-bearing Telegram request path is never written to
normal application logs. GET `/api/v1/settings/notifications` returns
`bot_token_set` and never the token itself.

Leave both `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` empty to disable delivery.
If only one is configured, the server records a configuration error without
failing agent report ingestion. Incomplete dashboard Telegram settings produce
the same validation messages (missing bot token, chat ID, or API base URL).

## Test message

`POST /api/v1/notifications/test` with `channel: "telegram"` sends a single
message:

```text
🚀 Homelab Monitor Test
Time: <ISO timestamp>
Server: <environment / hostname>
Version: <application version>
Status: ok
```

The Settings page (admin) shows Configured or Not configured, Last test, and a
Test Message button. Delivery failures (timeout, network, HTTP, invalid token,
invalid chat ID) become `DeliveryError` and are stored as `failed` history rows.
Successful deliveries are stored as `sent`. The dispatcher retries three times
without changing its architecture.

## Delivery behavior

Metric alerts are queued as FastAPI background tasks after alert state commits.
Offline-agent alerts are sent after the periodic liveness transaction commits.
Telegram failures are logged and do not roll back reports or alert state.

Live alert delivery in v1.0.0-rc1 uses the in-memory notification queue and
Telegram worker. See [notifications.md](notifications.md) and
[known-limitations.md](known-limitations.md). Tests replace the HTTP transport
and never contact the public Telegram service.

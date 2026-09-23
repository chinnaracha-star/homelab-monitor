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
```

The Bot API base URL is configurable and is not embedded in the notifier.
`TELEGRAM_BOT_TOKEN` is loaded as a secret value. HTTP client logging is held at
warning level so the token-bearing Telegram request path is never written to
normal application logs. GET `/api/v1/settings/notifications` returns
`bot_token_set` and never the token itself.

## Internal URL vs public URL

Telegram inline buttons can only open **public HTTP(S) URLs**. Docker Compose
hostnames such as `http://dashboard:8080` are valid for **internal health
checks** and invalid for Telegram. If a button URL is rejected, Telegram drops
the **entire** message (`Wrong HTTP URL`).

| Setting | Used for |
| --- | --- |
| `HOMELAB_DASHBOARD_HEALTH_URL` | API → dashboard probe inside Docker |
| `HOMELAB_API_HEALTH_URL` | Internal API health (Compose/monitoring) |
| `HOMELAB_DASHBOARD_PUBLIC_URL` | Telegram, email, QR, mobile Dashboard button |
| `HOMELAB_IMMICH_PUBLIC_URL` | Telegram / operator Immich button |
| `HOMELAB_QNAP_PUBLIC_URL` | Telegram / operator QNAP button |

If `HOMELAB_DASHBOARD_PUBLIC_URL` is empty, Telegram uses the Tailnet hostname
when it is a public HTTPS name (`https://home-srv-01.tail1ea57f.ts.net`). If that
is also unavailable, the message is sent **without buttons**. Internal URLs are
never attached.

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

Validation rules for those URLs live in `shared/public-url-rules.json` (see
[Public URL validation](public-url-validation.md)). Backend and dashboard load
the same file.

The Settings page (admin) shows Configured or Not configured, Last test, and a
Test Message button. The **Public URLs** editor validates Dashboard, Immich, and
QNAP addresses while typing. Health URLs (`http://dashboard:8080`) stay
internal. Public URLs are the only values Telegram buttons may use.

**GOOD**

- `https://home-srv-01.tail1ea57f.ts.net`
- `https://example.com`

**BAD**

- `http://dashboard:8080` (Docker-only)
- `http://localhost` / `http://127.0.0.1`
- `ftp://...`

Empty fields omit that button. Invalid fields never block Save; Telegram still
delivers text without that button. Changing the Settings Public URL fields does
not change live Telegram delivery (server env / Tailnet still apply).

Delivery failures (timeout, network, HTTP, invalid token,
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

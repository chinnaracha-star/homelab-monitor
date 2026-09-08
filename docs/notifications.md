# Notification center

Alert event types are unchanged. After alert state commits, HomeLab Monitor
dispatches messages through a notification layer with pluggable providers.

## Channels

| Channel | Provider | Recipient |
| --- | --- | --- |
| Telegram | Existing `TelegramNotifier` | Chat ID |
| Discord | Incoming webhook | Webhook URL (masked in API responses) |
| Slack | Incoming webhook | Webhook URL (masked in API responses) |
| Email | SMTP STARTTLS | To address |

Environment Telegram settings remain the fallback when dashboard settings are
empty. Dashboard admins can override or add Discord, Slack, and email in
Settings. Secrets are stored in `notification_settings.payload` and never
returned by GET.

## Delivery

`dispatch_alert_events()` still runs after report ingest and offline evaluation.
It now records a `notifications` row per channel, retries failed HTTP/SMTP
attempts three times, and publishes existing WebSocket events
`overview_updated` and `alert_updated` with `reason=notification_updated`.

Statuses: `pending`, `sent`, `failed`.

## APIs

| Method | Path | Roles |
| --- | --- | --- |
| `GET` | `/api/v1/notifications` | admin, operator, viewer |
| `GET` | `/api/v1/notifications/{id}` | admin, operator, viewer |
| `POST` | `/api/v1/notifications/test` | admin, operator |
| `POST` | `/api/v1/notifications/{id}/retry` | admin, operator |
| `GET` | `/api/v1/settings/notifications` | admin, operator, viewer |
| `PUT` | `/api/v1/settings/notifications` | admin |

Error codes: `notification_not_found`, `notification_channel_unconfigured`,
`permission_denied`, `auth_required`.

## Dashboard

- Settings (admin): channel configuration and test buttons. Telegram shows
  Configured or Not configured, Last test, and Test Message. The bot token is
  never displayed.
- Notifications: delivery history. Operators and admins can send a test and
  retry failures. Viewers are read-only.

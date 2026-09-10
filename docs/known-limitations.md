# Known limitations (v1.0.0-rc1)

These are accepted gaps for the first release candidate. They are not defects
to hotfix in 11.5.x unless product direction changes. Planned for **v1.1**
unless noted.

## Notifications

- **Queue is in-memory.** Pending Telegram jobs disappear if the API process
  restarts.
- **Delivery history resets after restart.** `GET /api/v1/notifications/delivery-history`
  and metrics use a process-local ring buffer (max 1000 stored, 100 returned).
- **Discord, Slack, and email are not on the live alert path.** The alert engine
  enqueues Telegram only. Dashboard Settings may still expose other channel
  fields; they do not deliver alert activate/recover messages in this RC.
- **Telegram uses environment settings** (`TELEGRAM_*` / `HOMELAB_TELEGRAM_*`),
  not a durable substitute for a multi-provider outbox.

## Data and operations

- **SQLite** is the only supported database. There is no documented backup or
  restore procedure for the `homelab-data` volume in this RC.
- **Infrastructure mock mode** defaults to `true`. Photo Services and QNAP
  snapshots are synthetic until URLs and credentials are set and mock is
  disabled.
- **OpenAPI** (`/docs`, `/openapi.json`) stays enabled in production images.
- **Compose** has no CPU/memory limits. JSON log rotation is in
  `docker-compose.prod.yml`, not the base file.

## Product scope deferred

UPS monitoring, agent auto-update, PostgreSQL, Prometheus/Grafana, Kubernetes,
and writing/controlling NAS or backup jobs remain out of scope.

## Related docs

- [Release notes](release-notes-v1.0.0-rc1.md)
- [Notifications](notifications.md)
- [Telegram](telegram.md)
- [Infrastructure](infrastructure.md)

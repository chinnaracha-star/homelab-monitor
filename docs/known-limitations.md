# Known limitations (v1.0.0-rc1)

Accepted gaps for the first release candidate. They are not RC1 blockers.
Planned follow-up: [roadmap-v1.1.md](roadmap-v1.1.md).

## Notifications

- **Queue is in-memory.** Pending Telegram alert jobs disappear if the API
  process restarts. **Durability is postponed to v1.1.** No database outbox in
  10.3.x.
- **Delivery history resets after restart.** Notification Center metrics use a
  process-local ring buffer (max 1000 stored, 100 returned).
- **Discord, Slack, and email are not on the live alert path.** Settings may
  still show other channel fields.
- **Telegram** uses environment settings. Empty token/chat means no delivery
  even when `HOMELAB_TELEGRAM_ENABLED=true`.
- **Scheduled reports** persist last-sent in SQLite; that is not the alert FIFO.
- Hourly reports default **off**.

## Data and operations

- **SQLite only.** Host scripts cover backup/verify/restore/rotation
  ([backup.md](backup.md)). Compose does not snapshot volumes automatically.
- **Infrastructure mock** defaults to `true`. Immich, QNAP, Photo Services, and
  the Backup observer are synthetic until mock is off and URLs are set. Photo
  **Monitor** folder poll does not use mock mode.
- **OpenAPI** (`/docs`, `/openapi.json`, `/redoc`) is proxied on the dashboard
  origin (loopback and Tailscale). It is not a WAN publish.
- **CPU/memory limits** apply when using `docker-compose.prod.yml`.
- **Production-health Dashboard probe** is `unknown` when
  `HOMELAB_DASHBOARD_HEALTH_URL` is empty (so Telegram is not given
  `http://dashboard:8080`).
- **Photo Monitor** is CIFS poll (not inotify). HEIC may fall back from
  `sendPhoto` to text.
- **Agent protocol** stays `0.1.0` while the app is `1.0.0-rc1`.
- Uncommitted local changes are not a substitute for a tagged git release.

## Product scope deferred

UPS monitoring, agent auto-update, PostgreSQL, Prometheus/Grafana, Kubernetes,
WAN Funnel, and writing/controlling NAS or backup jobs.

## Related docs

- [Release notes](release-notes-v1.0.0-rc1.md)
- [Production readiness](production-readiness.md)
- [Operator runbook](operator-runbook.md)
- [Notifications](notifications.md)
- [Telegram](telegram.md)
- [Infrastructure](infrastructure.md)
- [Production checklist](production-checklist.md)
- [Production hardening](production-hardening.md)

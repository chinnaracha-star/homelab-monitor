# Production hardening report (sprint 10.3.4)

Date: 2026-09-11. No product features were added. Notification durability was
reviewed and **explicitly postponed** (no database outbox).

## SQLite backup

Host scripts:

- `scripts/backup.sh` — `sqlite3 .backup`, `PRAGMA integrity_check`, `SHA256SUMS`
- `scripts/verify-backup.sh`
- `scripts/restore.sh` (stop API first; drop leftover WAL/SHM)
- `scripts/rotate-backups.sh` (`HOMELAB_BACKUP_KEEP_DAYS`, default 14)

Live `.env` is not packed by default. Operator guide: [backup.md](backup.md).

## Notification queue

`NotificationQueue` is a process-local FIFO (`deque` + lock). Alert jobs and
delivery history die on API restart. **v1.1** is the planned durable outbox.
Scheduled report last-sent timestamps remain in SQLite `notification_settings`.

## Nginx / PWA

`deploy/nginx/nginx.conf` and `homelab-monitor.conf` now share:

- hashed `/assets/` immutable cache
- no-store SPA / service worker (`sw.js`, `service-worker.js`, `workbox-*.js`)
- `offline.html` no-cache
- CSP, nosniff, DENY frames, Referrer-Policy, Permissions-Policy
- OpenAPI `/docs`, `/redoc`, `/openapi.json` still proxied (loopback + Tailscale)

## Docker / Compose

| Control | Status |
| --- | --- |
| Restart | `unless-stopped` |
| Health | API `/health` 30s/5s/3 retries, 40s start; dashboard `GET /` |
| Logging | json-file `10m` × 5 on both services in the **base** file |
| Limits | prod overlay: API 768m / 1 CPU; dashboard 128m / 0.5 CPU |
| Volumes | `homelab-data`, `homelab-logs` |
| Photo | six NAS paths `:ro` |
| Dashboard | `127.0.0.1:18081` → container 8080 |
| API | `expose 8000` only, `backend` + `egress` |
| Tailscale | overlay mounts socket `:ro`; Serve on host 18081 |

## Open issues

- OpenAPI remains reachable through nginx (accepted for this RC).
- Empty `HOMELAB_DASHBOARD_HEALTH_URL` leaves production-health Dashboard check
  `unknown`.
- Photo bind mounts fail if host CIFS paths are missing (Compose still starts).
- Backup scripts need `sqlite3` on the host for the safest copy.
- In-memory alert queue (see known limitations).

## Known limitations

See [known-limitations.md](known-limitations.md). Queue durability, mock-on
default, and OpenAPI exposure are unchanged product decisions.

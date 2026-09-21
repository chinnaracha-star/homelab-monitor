# Project status

**Current version:** `1.0.0-rc2`  
**Current phase:** 11  
**Current sprint:** 11.5 (Operations Center) after 11.3.1 RC2 baseline  
**Git branch:** `main` (working tree dirty; not committed)

## Architecture

Ubuntu agents report over HTTPS to nginx. FastAPI stores SQLite history, evaluates alerts, and can notify Telegram. The React dashboard is a static PWA. Scheduled gzip SQLite backups run in the API process. No PostgreSQL.

```text
Agents --> nginx --> FastAPI + SQLite
                 --> React PWA
                 --> Telegram / Photo Monitor / Backup scheduler
```

## Completed features

- Agent/server monitoring, JWT RBAC, alerts, analytics, capacity, insights
- Photo Services (read-only) and Photo Monitor (CIFS poll + Telegram)
- Sprint 10.3.x production config, hardening, RC1 certification
- Sprint 11.1 SQLite backup, retention, verification, restore docs
- Sprint 11.2 observability on Production Health
- Sprint 11.3 multi-agent fleet summaries on the Agents page
- Sprint 11.4 performance/reliability scores and 24h/7d/30d windows
- Sprint 11.5 operator actions on Production Health (confirm + history)

## Open risks

- Running Docker API image may lag this working tree until rebuild
- Notification queue is still in-memory
- SQLite backups share `homelab-data` unless copied off-host
- Restart API/Dashboard from the UI requires Docker CLI inside the API container (often missing)
- `HOMELAB_INFRASTRUCTURE_MOCK` still defaults to true in examples

## Deployment status

Compose: API unpublished, dashboard loopback. Live backup proven on host `data/backups`. Telegram depends on env. Production Health is available to admin and operator.

## Next sprint

Phase 11.6 / v1.1 planning: durable notification outbox, off-host backup copies, optional resource limits. Do not start until RC2 is tagged.

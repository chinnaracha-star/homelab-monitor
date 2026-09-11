# Production readiness report — v1.0.0-rc1

**Certification sprint:** 10.3.5  
**Date:** 2026-09-11  
**Scope:** validation and documentation only. Live API/dashboard were **not**
restarted (in-memory notification queue).

**Gates:** `ruff check` pass; `pytest` pass; `npm test` 169 pass; `npm run build`
pass (`dist/sw.js`); `docker compose config --quiet` pass.

**Live probes (2026-09-11):** `GET http://127.0.0.1:18081/health` →
`healthy`, `version` `1.0.0-rc1`, `database` `up`. Dashboard `/`, `/login`,
`/openapi.json`, `/manifest.webmanifest` → HTTP 200. Compose: API and dashboard
**healthy**. Tailscale Serve: HTTPS origin proxies `http://127.0.0.1:18081`
(tailnet only).

Legend: **PASS** = certified for RC1. **WARNING** = works with accepted limits
or operator action. **FAIL** = blocks RC1. No FAIL items in this audit.

| Subsystem | Result | Evidence |
| --- | --- | --- |
| Authentication | **PASS** | JWT + RBAC tests; bootstrap passwords required in production |
| Dashboard | **PASS** | Live HTTP 200 on loopback 18081; pages and permission routes present |
| Agent | **PASS** | Protocol `0.1.0`; outbound HTTPS; transport/buffer tests |
| Alerts | **PASS** | Engine, rules, stability, timeline, incidents tests |
| Notification Center | **WARNING** | APIs and UI ship; queue/history in-memory |
| Telegram | **WARNING** | Code/tests/config enabled; live Bot API send not executed in this sprint |
| Photo Monitor | **WARNING** | Poll + tests; CIFS delay; HEIC `sendPhoto` may fall back to text |
| Immich | **WARNING** | GET-only connector; mock **ON** by default |
| Backup (observer) | **WARNING** | Dashboard Backup page; mock **ON** by default |
| Backup (SQLite) | **PASS** | `scripts/backup.sh` / verify / restore / rotate + tests |
| Analytics | **PASS** | API + dashboard tests |
| Capacity | **PASS** | API + dashboard tests |
| Insights | **PASS** | API + dashboard tests |
| Developer | **PASS** | Developer page + tests; version `1.0.0-rc1` |
| Production Health | **WARNING** | Page + APIs; empty `HOMELAB_DASHBOARD_HEALTH_URL` → Dashboard check `unknown` |
| PWA | **PASS** | Manifest 200; nginx SW cache headers aligned; `sw.js` build |
| Tailscale | **PASS** | Serve running to loopback 18081 (tailnet only, no Funnel) |
| Remote Access | **PASS** | Overlay + status API + docs; socket read-only |
| Scheduler | **PASS** | Hourly/daily/weekly report loop; hourly **off** by default |
| SQLite | **PASS** | Health `database=up`; Alembic 0001–0010 |
| Compose | **PASS** | Config valid; dashboard loopback; API unpublished |
| Docker | **PASS** | Both containers healthy; restart `unless-stopped` |
| Health endpoint | **PASS** | Live `/health` JSON as above |
| Restart API | **WARNING** | Policy `unless-stopped`; **not bounced** (would drop alert queue) |
| Restart Dashboard | **WARNING** | Same; nginx healthcheck present |
| Restart Compose | **WARNING** | `docker compose restart` documented in runbook, not executed |

## Scores

| Metric | Value |
| --- | --- |
| Production score | **86 / 100** |
| Deployment ready | **84%** |
| FAIL count | **0** |

Weighted: PASS = 100, WARNING = 60, FAIL = 0 across the table above.

## Remaining risks

1. Uncommitted 10.3.3–10.3.5 work is not in git `main`; live images may predate nginx/backup script changes until rebuild.
2. `HOMELAB_INFRASTRUCTURE_MOCK=true` until the operator turns it off.
3. API restart loses pending Telegram alerts and Notification Center metrics.
4. OpenAPI remains on the dashboard origin (loopback + Tailscale).
5. Photo Monitor depends on host CIFS mounts existing.
6. Telegram delivery still needs token + chat ID in the host `.env`.

Related: [operator-runbook.md](operator-runbook.md), [known-limitations.md](known-limitations.md), [roadmap-v1.1.md](roadmap-v1.1.md).

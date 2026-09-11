# Release notes — v1.0.0-rc1

**Version:** `1.0.0-rc1`  
**Certified:** 2026-09-11 (sprint 10.3.5)  
**Status:** Release candidate for a trusted HomeLab LAN with Tailscale Serve in
front of loopback `127.0.0.1:18081`.

Package, API, dashboard PWA, and `GET /health` report **`1.0.0-rc1`**. Agent
protocol remains **`0.1.0`**. Telegram report footer sprint **`10.2.8.3`**.

## Highlights

- Ubuntu agents, FastAPI, SQLite, JWT RBAC, React dashboard (PWA)
- Docker Compose: API unpublished, dashboard loopback, healthchecks, non-root
- Alerts, incidents, timeline, analytics, capacity, insights, predictions
- Telegram alerts, executive reports, Photo Monitor (CIFS poll, `sendPhoto`)
- Read-only Immich / QuMagie / QNAP / backup observer (mock **ON** by default)
- Production Health and Developer pages
- Tailscale Serve overlay (status only inside the API; Serve stays on the host)
- Host SQLite backup / verify / restore / rotate scripts

## Breaking changes (from early internals)

- No shipped dashboard passwords. Set `HOMELAB_BOOTSTRAP_ADMIN_PASSWORD`.
- Live alerts are **Telegram-only**.
- Dashboard host port default is **18081** (container nginx still listens on
  8080).

## Operator docs

- [Production readiness](production-readiness.md)
- [Operator runbook](operator-runbook.md)
- [Production checklist](production-checklist.md)
- [Production hardening](production-hardening.md)
- [Known limitations](known-limitations.md)
- [v1.1 roadmap](roadmap-v1.1.md)

## Certification gates (2026-09-11)

`ruff check`, full `pytest`, dashboard `npm test` + `npm run build`,
`docker compose config --quiet`. Live `/health` healthy. Tailscale Serve on
18081. API/dashboard **not** restarted during certification.

## Upgrade

1. Copy `.env.production.example` → `.env`; set secrets and bootstrap admin.
2. Set Telegram token/chat ID.
3. `docker compose up -d --build`
4. Confirm `GET /health` `version` `1.0.0-rc1`.
5. Optional: prod + Tailscale overlays; `sudo tailscale serve --bg 18081`.

See [CHANGELOG.md](../CHANGELOG.md) and [README](../README.md).

# HomeLab Monitor Toolkit

HomeLab Monitor Toolkit is an agent-server platform for a trusted home lab:
Ubuntu hosts, Docker, Immich/QuMagie photo pipelines, and QNAP NAS snapshots.
Python agents send authenticated health reports to a FastAPI server. The server
stores history, evaluates alerts, can notify Telegram, and serves a React
dashboard.

> **v1.0.0-rc1** — first release candidate. Set bootstrap passwords before
> exposing the dashboard. See [release notes](docs/release-notes-v1.0.0-rc1.md),
> [changelog](CHANGELOG.md), and [known limitations](docs/known-limitations.md).

## Architecture

```text
Ubuntu agents --HTTPS POST--> nginx -- /api --> FastAPI --SQLite--> History and alerts
                                      |
                                      +--> React dashboard (static PWA)
                                      +--> /api/v1/ws/dashboard (WebSocket)
                                      +--> Telegram (live alerts in rc1)
```

Agents only make outbound connections (default 60s). They do not open inbound
ports. More detail: [architecture](docs/architecture.md).

## Quick Start

Requirements: Python 3.12+, `python3-venv`, Node.js 22+ for the dashboard.

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env
# Set HOMELAB_REGISTRATION_KEY, HOMELAB_JWT_SECRET, and
# HOMELAB_BOOTSTRAP_ADMIN_PASSWORD
.venv/bin/alembic upgrade head
.venv/bin/uvicorn homelab_monitor.main:app --reload
```

API: `http://127.0.0.1:8000` — OpenAPI `/docs`, health `/health`.

```bash
cd dashboard
npm install
npm run dev
```

Log in at `/login` with the bootstrap admin user. JWT, roles, and user admin:
[authentication](docs/authentication.md), [RBAC](docs/rbac.md),
[user management](docs/user-management.md).

## Docker deployment

```bash
cp .env.production.example .env
# Replace secrets and HOMELAB_BOOTSTRAP_ADMIN_PASSWORD
docker compose up -d --build
curl -fsS http://127.0.0.1:8080/health
```

Only the dashboard is published (`127.0.0.1:8080` by default). Nginx proxies
`/api`, `/ws`, and `/health`. Production overlay and Tailscale Serve:
[docker](docs/docker.md), [deployment](docs/deployment.md),
[nginx](docs/nginx.md), [remote access](docs/remote-access.md), [PWA](docs/pwa.md).

## Environment variables

Copy [`.env.example`](.env.example) or [`.env.production.example`](.env.production.example).
Never commit a filled-in `.env`.

| Variable | Role |
| --- | --- |
| `HOMELAB_ENVIRONMENT` | `development` or `production` |
| `HOMELAB_REGISTRATION_KEY` | Agent registration (min 24 chars) |
| `HOMELAB_JWT_SECRET` | Dashboard JWT (min 32 chars) |
| `HOMELAB_BOOTSTRAP_ADMIN_PASSWORD` | Required in production to create/rotate `admin` |
| `HOMELAB_BOOTSTRAP_OPERATOR_PASSWORD` | Optional; creates `operator` when set |
| `HOMELAB_BOOTSTRAP_VIEWER_PASSWORD` | Optional; creates `viewer` when set |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | Telegram Bot API |
| `HOMELAB_TELEGRAM_ENABLED` | Delivery on/off (`false` in examples) |
| `HOMELAB_NOTIFICATION_WORKER_ENABLED` | Background Telegram worker |
| `HOMELAB_INFRASTRUCTURE_MOCK` | Synthetic NAS/photo snapshots when `true` |
| `HOMELAB_QNAP_*` / `HOMELAB_IMMICH_*` / `HOMELAB_QUMAGIE_*` | Live connectors |

Thresholds, forwarded IPs, and log paths are documented in the example files.

## Telegram setup

1. Create a bot with BotFather and note the chat ID.
2. Set `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `HOMELAB_TELEGRAM_ENABLED=true`.
3. Restart the API so the notification worker can send.

Alert activate/recover messages are queued, batched (10s), and retried up to
three times. Guide: [telegram](docs/telegram.md).

## Photo Scanner

The dashboard **Photo Services** page is a read-only observer of Immich, QuMagie,
and QNAP photo storage. It never uploads, indexes, or deletes files. Mock mode
is the default until live URLs and API keys are configured.
[photo-services](docs/photo-services.md).

## QNAP / NAS integration

Infrastructure connectors issue **GET**-only snapshots for QNAP, Docker, Immich,
QuMagie, and backup targets. One failed connector does not fail the others.
[infrastructure](docs/infrastructure.md), [backup](docs/backup.md).

## Notification Center

Path: `/monitoring/notifications`. The page shows delivery metrics, a filterable
history table (max 100 rows), and the existing notification timeline.

Live alert delivery in rc1 is **Telegram only**. Queue and history live in
process memory. [notifications](docs/notifications.md),
[known limitations](docs/known-limitations.md).

## Ubuntu agent

```bash
.venv/bin/homelab-agent collect
.venv/bin/homelab-agent --env-file ./agent.env run
```

Register via [docs/api.md#register-an-agent](docs/api.md#register-an-agent).
Failed reports stay in a local SQLite queue. [agent](docs/agent.md).

Alerts use [alert rules](docs/alert-rules.md). History charts:
[history](docs/history.md). Groups: [groups](docs/groups.md). Live UI:
[realtime](docs/realtime.md).

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| API exits immediately in Docker | `HOMELAB_ENVIRONMENT=production` requires `HOMELAB_BOOTSTRAP_ADMIN_PASSWORD` (not `admin123`) |
| Cannot log in | Bootstrap env on first start; JWT secret unchanged after tokens were issued |
| No Telegram messages | Token, chat ID, `HOMELAB_TELEGRAM_ENABLED=true`, worker enabled; history is empty after restart |
| Photo/QNAP data looks fake | `HOMELAB_INFRASTRUCTURE_MOCK=true` (default) |
| Dashboard empty after refresh | Confirm nginx `/api` proxy and `VITE_API_BASE_URL=/api/v1` in the image |
| Port 8080 busy | `HOMELAB_DASHBOARD_PORT=18081` |
| Health 503 | SQLite volume permissions / migrations (`alembic upgrade head`) |

Tests:

```bash
.venv/bin/pytest
.venv/bin/ruff check .
cd dashboard && npm run lint && npm run test && npm run build
```

## Version 1 scope

In rc1: Ubuntu agents, Docker/Immich/QNAP **read-only** views, REST + WebSocket
dashboard, SQLite, Telegram alerts, Compose.

Out of scope: UPS, agent auto-update, PostgreSQL, Prometheus/Grafana, Kubernetes,
controlling NAS or backup jobs. Tailscale is **read-only status** plus optional
host Serve; the API never configures Tailscale.

## License

[MIT](LICENSE)

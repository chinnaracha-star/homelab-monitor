# HomeLab Monitor Toolkit

HomeLab Monitor Toolkit is an agent-server monitoring platform for Ubuntu hosts,
Docker workloads, Immich, and QNAP. Lightweight Python agents collect local health data
and send authenticated reports to a central FastAPI server for history, alerting,
Telegram notifications, and a web dashboard.

> Status: early development. Sprint 6.3 packages the stack for Docker Compose
> and systemd production installs.

## Architecture

```text
Ubuntu agents --HTTPS POST--> nginx -- /api --> FastAPI --SQLite--> History and alerts
                                      |
                                      +--> React dashboard (static)
                                      +--> /api/v1/ws/dashboard (WebSocket)
                                      +--> Telegram
```

Agents initiate outbound connections every 60 seconds by default. They do not
expose inbound ports. The API response supplies the next reporting interval,
configuration revision, and supported agent-version policy.

## Sprint 1 development

Requirements:

- Python 3.12+
- `python3-venv` on Ubuntu (`sudo apt install python3-venv`)

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env
# Set HOMELAB_REGISTRATION_KEY and HOMELAB_JWT_SECRET in .env
.venv/bin/alembic upgrade head
.venv/bin/uvicorn homelab_monitor.main:app --reload
```

The API is available at `http://127.0.0.1:8000`, with OpenAPI documentation at
`/docs` and the health endpoint at `/health`.

Production deployment uses Docker Compose or systemd. The dashboard nginx
container (or host nginx) serves the UI and proxies `/api`, `/ws`, and
`/health`. See [deployment](docs/deployment.md), [docker](docs/docker.md),
[nginx](docs/nginx.md), and [backup](docs/backup.md).

The dashboard is a Vite app in `dashboard/`. After logging in at `/login` it
calls the protected Dashboard API.

```bash
cd dashboard
npm install
npm run dev
```

Dashboard clients authenticate with a JWT and then read:

- `/api/v1/dashboard/overview`
- `/api/v1/agents`
- `/api/v1/agents/{agent_id}`
- `/api/v1/agents/{agent_id}/latest-report`

Default logins after migration (or after the next API start on an older `0003`
database): `admin` / `admin123`, `operator` / `operator123`, and
`viewer` / `viewer123`. See [authentication](docs/authentication.md),
[RBAC](docs/rbac.md), and [user management](docs/user-management.md).

After login the dashboard also opens `GET /api/v1/ws/dashboard` with the JWT.
Live events refresh Overview, Agents, Agent Detail, and Alerts immediately.
If the socket drops, last-loaded data stays on screen, a reconnect banner is
shown, and 30-second REST polling continues until the connection returns. See
[realtime](docs/realtime.md).

Agent Detail also loads `GET /api/v1/history/agents/{agent_id}` for the selected
time range and charts CPU, memory, disk, and temperature. See
[history](docs/history.md).

The server also persists active and resolved alert state for CPU, memory, disk,
temperature, and offline agents. New alert transitions can be delivered through
the reusable [Telegram notifier](docs/telegram.md).

## Ubuntu agent

Collect one local snapshot without connecting to the server:

```bash
.venv/bin/homelab-agent collect
```

Register the host through the API, copy the one-time token, and create an
environment file from `deploy/systemd/agent.env.example`. Start the scheduled
agent manually:

```bash
.venv/bin/homelab-agent --env-file ./agent.env run
```

The server controls the next reporting interval. Failed reports are retained in
a bounded local SQLite queue and retried in order with their original report IDs.
The [registration example](docs/api.md#register-an-agent) reads the bootstrap
key directly from `.env` using `python-dotenv`; no shell export is required. See
[the agent guide](docs/agent.md) for configuration, systemd, and troubleshooting.

Run tests and lint checks:

```bash
.venv/bin/pytest
.venv/bin/ruff check .
.venv/bin/ruff format --check .
cd dashboard && npm run lint && npm run test && npm run build
```

## Version 1 scope

- Ubuntu agents
- Docker and Immich monitoring
- Basic QNAP monitoring through SSH/API
- REST API, WebSocket dashboard updates, and config sync
- SQLite history and health scores
- Telegram alerts and recovery notifications
- React dashboard
- Docker Compose deployment

UPS, Tailscale, Nginx, advanced SMART data, PostgreSQL,
Prometheus, Grafana, Kubernetes, and agent auto-update are deferred.

## License

[MIT](LICENSE)

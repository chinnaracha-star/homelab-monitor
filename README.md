# HomeLab Monitor Toolkit

HomeLab Monitor Toolkit is an agent-server monitoring platform for Ubuntu hosts,
Docker workloads, Immich, and QNAP. Lightweight Python agents collect local health data
and send authenticated reports to a central FastAPI server for history, alerting,
Telegram notifications, and a web dashboard.

> Status: early development. Sprint 5.2 enforces dashboard role-based access
> control on top of JWT authentication.

## Architecture

```text
Ubuntu agents --HTTPS POST--> FastAPI --SQLite--> History and alerts
                                      |
                                      +--> Telegram
                                      +--> React dashboard
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
```

## Version 1 scope

- Ubuntu agents
- Docker and Immich monitoring
- Basic QNAP monitoring through SSH/API
- REST API and config sync
- SQLite history and health scores
- Telegram alerts and recovery notifications
- React dashboard
- Docker Compose deployment

UPS, Tailscale, Nginx, advanced SMART data, PostgreSQL,
Prometheus, Grafana, Kubernetes, WebSockets, and agent auto-update are deferred.

## License

[MIT](LICENSE)

# HomeLab Monitor Toolkit

HomeLab Monitor Toolkit is an agent-server monitoring platform for Ubuntu hosts,
Docker workloads, Immich, and QNAP. Lightweight Python agents collect local health data
and send authenticated reports to a central FastAPI server for history, alerting,
Telegram notifications, and a web dashboard.

> Status: early development. Phase 8.3 adds read-only backup monitoring for a
> TS-253 Pro target. Agent protocol, alert engine, alert rules, notifications,
> JWT, groups, history, existing REST APIs, and WebSocket event types remain in
> place.

## Architecture

```text
Ubuntu agents --HTTPS POST--> nginx -- /api --> FastAPI --SQLite--> History and alerts
                                      |
                                      +--> React dashboard (static)
                                      +--> /api/v1/ws/dashboard (WebSocket)
                                      +--> Telegram / Discord / Slack / email
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
- `/api/v1/groups`
- `/api/v1/groups/summary`
- `/api/v1/groups/{group_id}`

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

Agents can be organized into groups. Admins and operators create groups and
assign membership; viewers can list groups and open group detail. See
[groups](docs/groups.md).

The server also persists active and resolved alert state for CPU, memory, disk,
temperature, and offline agents. Thresholds come from
[configurable alert rules](docs/alert-rules.md). Alert transitions are delivered
through the [notification center](docs/notifications.md) (Telegram, Discord,
Slack, email). Telegram environment variables still work as a fallback; see
[telegram](docs/telegram.md).

Read-only [infrastructure connectors](docs/infrastructure.md) expose QNAP,
Docker, Immich, QuMagie, and backup snapshots to the dashboard. The
[Photo Services](docs/photo-services.md) page is a read-only view of Immich,
QuMagie, and QNAP storage. The [Backup](docs/backup.md) page observes
replication to a TS-253 Pro target and never controls jobs.

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

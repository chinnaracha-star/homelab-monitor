# HomeLab Monitor Toolkit

HomeLab Monitor Toolkit is an agent-server monitoring platform for Ubuntu hosts,
Docker workloads, Immich, and QNAP. Lightweight agents collect local health data
and send authenticated reports to a central FastAPI server for history, alerting,
Telegram notifications, and a web dashboard.

> Status: early development. Sprint 1 implements the central API, agent registration,
> metrics ingestion, SQLite persistence, and configuration sync.

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
.venv/bin/alembic upgrade head
.venv/bin/uvicorn homelab_monitor.main:app --reload
```

The API is available at `http://127.0.0.1:8000`, with OpenAPI documentation at
`/docs` and the health endpoint at `/health`.

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

UPS, Tailscale, Nginx, advanced SMART data, multi-user access, PostgreSQL,
Prometheus, Grafana, Kubernetes, WebSockets, and agent auto-update are deferred.

## License

[MIT](LICENSE)

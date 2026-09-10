# Deployment

Production options:

1. Docker Compose (recommended)
2. systemd units on an Ubuntu host

Version 1 is intended for a trusted HomeLab LAN behind HTTPS termination.
Do not expose the API port directly to the internet.

## Docker Compose

See [docker.md](docker.md).

```bash
cp .env.production.example .env
# Replace HOMELAB_REGISTRATION_KEY, HOMELAB_JWT_SECRET, and HOMELAB_BOOTSTRAP_ADMIN_PASSWORD
docker compose up -d --build
```

`.env` is optional for Compose; if it is missing, pass
`--env-file .env.production.example` only for a dry run. Production must use a
private `.env` with unique secrets.

The dashboard listens on `http://127.0.0.1:8080` by default (`HOMELAB_DASHBOARD_PORT`
overrides the host port). The API is not published on the host; nginx proxies
`/api`, `/ws`, and `/health`.

Production bind to loopback HTTP:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

That publishes `127.0.0.1:80`. Put TLS on a LAN reverse proxy or tunnel in
front of it.

For phones and laptops outside the home, use Tailscale Serve against loopback
instead of a public proxy. See [remote-access.md](remote-access.md). Example:

```bash
export HOMELAB_DASHBOARD_PORT=18081
docker compose -f docker-compose.yml -f docker-compose.tailscale.yml up -d --build
sudo tailscale serve --bg 18081
```

Local `http://localhost:18081` remains available. Do not port-forward.

## systemd

Assumes the repository is cloned to `/opt/homelab-monitor`.

1. Create the service user and directories:

```bash
sudo apt install nginx sqlite3 python3-venv
sudo systemctl disable --now nginx.service
sudo useradd --system --home /opt/homelab-monitor --shell /usr/sbin/nologin homelab-monitor
sudo mkdir -p /opt/homelab-monitor /etc/homelab-monitor /var/lib/homelab-monitor \
  /var/log/homelab-monitor /var/www/homelab-monitor
sudo chown -R homelab-monitor:homelab-monitor \
  /opt/homelab-monitor /var/lib/homelab-monitor /var/log/homelab-monitor
```

2. Install the Python project as that user:

```bash
sudo -u homelab-monitor python3 -m venv /opt/homelab-monitor/.venv
sudo -u homelab-monitor /opt/homelab-monitor/.venv/bin/pip install /opt/homelab-monitor
```

3. Copy environment and units:

```bash
sudo cp /opt/homelab-monitor/.env.production.example /etc/homelab-monitor/api.env
sudo chmod 600 /etc/homelab-monitor/api.env
# Edit secrets, then:
sudo cp /opt/homelab-monitor/deploy/systemd/api.service \
  /etc/systemd/system/homelab-monitor-api.service
sudo cp /opt/homelab-monitor/deploy/systemd/dashboard.service \
  /etc/systemd/system/homelab-monitor-dashboard.service
```

Set `HOMELAB_DATABASE_URL=sqlite:////var/lib/homelab-monitor/homelab-monitor.db`
and `HOMELAB_LOG_DIR=/var/log/homelab-monitor` in `api.env`.

4. Build the dashboard and install nginx configuration:

```bash
cd /opt/homelab-monitor/dashboard
sudo -u homelab-monitor npm ci
sudo -u homelab-monitor npm run build
sudo cp -r /opt/homelab-monitor/dashboard/dist/* /var/www/homelab-monitor/
sudo cp /opt/homelab-monitor/deploy/nginx/nginx.host.conf /etc/homelab-monitor/nginx.conf
sudo cp /opt/homelab-monitor/deploy/nginx/homelab-monitor.conf /etc/homelab-monitor/homelab-monitor.conf
```

See [nginx.md](nginx.md).

5. Enable services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now homelab-monitor-api.service
sudo systemctl enable --now homelab-monitor-dashboard.service
```

The Ubuntu agent unit remains `deploy/systemd/homelab-agent.service`. See
[agent.md](agent.md#run-with-systemd) for enable/start commands. Point
`HOMELAB_SERVER_URL` at `http://<host>/api/v1` when nginx is in front of the
API, or `http://127.0.0.1:8000/api/v1` on the same host without nginx.

## Health

- API: `GET /health`
- Through nginx: `GET /health` on the dashboard port
- Dashboard UI: `GET /`

## Defaults

Set `HOMELAB_BOOTSTRAP_ADMIN_PASSWORD` in `.env` before the first production start.

## Backup

See [backup.md](backup.md).

# Production checklist

Use this before the first real deployment. Copy `.env.production.example` to
`.env` (never commit it). There is no `docker-compose.production.yml`; the
production overlay is `docker-compose.prod.yml`.

Host dashboard port is **18081** everywhere: Compose, Settings `dashboard_port`,
Tailscale Serve, and this checklist.

## Startup order

1. Fill secrets in `.env` (registration key, JWT secret, bootstrap admin password).
2. Set Telegram token and chat ID (Telegram stays **enabled** in config; empty
   token still means no messages).
3. Decide Mock ON vs Mock OFF (below).
4. `docker compose up -d --build` (add `-f docker-compose.prod.yml` and/or
   `-f docker-compose.tailscale.yml` as needed).
5. `sudo tailscale serve --bg 18081` for phones and laptops on the tailnet.
6. Confirm `curl -fsS http://127.0.0.1:18081/health`.

## Telegram

- `HOMELAB_TELEGRAM_ENABLED=true` (Compose, Settings, and env examples agree).
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` required for delivery.
- `TELEGRAM_REQUEST_TIMEOUT=30`.
- `HOMELAB_NOTIFICATION_WORKER_ENABLED=true`.
- Queue and delivery history are in-memory (restart drops pending jobs).

## Dashboard URL

Do **not** set `HOMELAB_DASHBOARD_HEALTH_URL=http://dashboard:8080`. That is
Docker-internal DNS and is not a browser or Telegram URL.

Resolution used by the app (unchanged):

1. `HOMELAB_DASHBOARD_HEALTH_URL` when set (operator HTTPS or loopback).
2. Tailscale Serve / MagicDNS when the API can read Tailscale status.
3. `http://127.0.0.1:18081`.

Leave the variable empty unless you have a stable public Tailscale HTTPS origin.

## Dashboard port

- Compose host mapping: `127.0.0.1:18081` → container nginx `8080`.
- Container listen port **8080** stays internal (Dockerfile healthcheck, nginx).
- Production overlay uses the same host port **18081** (not host port 80).

## Infrastructure mock

| Mode | `HOMELAB_INFRASTRUCTURE_MOCK` | Effect |
| --- | --- | --- |
| **Mock ON** | `true` (default) | Photo Services, QNAP, Immich stats, and backup observer show synthetic snapshots. Safe when NAS URLs are empty. |
| **Mock OFF** | `false` | Live GET-only connectors. Set Immich, QNAP, and backup URLs first or those tiles error. |

Photo Monitor (folder poll + Telegram photos) does **not** use mock mode.

## Immich

- Mock ON: ignore `HOMELAB_IMMICH_*` for dashboard Photo Services.
- Mock OFF: set `HOMELAB_IMMICH_URL` and `HOMELAB_IMMICH_API_KEY`.
- Optional Telegram Immich button uses the same URL when configured.

## QNAP

- Mock ON: synthetic storage snapshot.
- Mock OFF: `HOMELAB_QNAP_URL` plus username/password or SID. Read-only.

## SQLite

- Compose path: `sqlite:////var/lib/homelab-monitor/homelab-monitor.db` on volume `homelab-data`.
- Run `alembic upgrade head` in the API image on start (existing image entrypoint).
- Backup: [backup.md](backup.md) (`./scripts/backup.sh`). There is still no
  automated volume snapshot in Compose.

## Photo Monitor

- `HOMELAB_PHOTO_WATCHER_ENABLED=true`.
- Folders must exist on the Ubuntu host and match Compose `:ro` mounts.
- Poll interval default 5s (CIFS; not inotify).
- Telegram photo send requires Telegram token/chat as above.

## Tailscale

- Overlay: `docker compose -f docker-compose.yml -f docker-compose.tailscale.yml up -d`.
- Serve: `sudo tailscale serve --bg 18081`.
- Do not enable Funnel. Do not WAN-forward 18081.
- Socket mount is read-only status only.

## Backup observer vs app backup

- Dashboard Backup page: mock ON until `HOMELAB_BACKUP_URL` and Mock OFF.
- Application SQLite backup: `scripts/backup.sh`, then `verify-backup.sh`.
  Rotate with `scripts/rotate-backups.sh`. See [backup.md](backup.md).
  Queue durability is **not** in those backups (in-memory).

## Bootstrap password

- Production **requires** `HOMELAB_BOOTSTRAP_ADMIN_PASSWORD` (not `admin123`).
- Operator/viewer accounts are created only when their passwords are set.
- After first boot, rotate in the Users page or by setting a new bootstrap
  password and restarting once.

## Health

- `http://127.0.0.1:18081/health`
- Empty `HOMELAB_DASHBOARD_HEALTH_URL` makes the production-health **Dashboard**
  check `unknown` (expected). Set it to the Tailscale HTTPS origin if the API
  can reach that URL.

# Operator runbook (v1.0.0-rc1)

Trusted HomeLab LAN or Tailscale Serve. Dashboard host port **18081**. API is
not published. Never commit `.env`. Full checklist:
[production-checklist.md](production-checklist.md).

## Start

```bash
cd /path/to/homelab-monitor
cp -n .env.production.example .env   # first time only; then edit secrets
docker compose up -d --build
# optional overlays:
# docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
# docker compose -f docker-compose.yml -f docker-compose.tailscale.yml up -d --build
curl -fsS http://127.0.0.1:18081/health
```

Production requires `HOMELAB_BOOTSTRAP_ADMIN_PASSWORD`,
`HOMELAB_REGISTRATION_KEY`, and `HOMELAB_JWT_SECRET`.

## Stop

```bash
docker compose stop
# or fully remove containers (keeps volumes):
docker compose down
```

`docker compose down -v` **deletes** SQLite and logs. Do not use `-v` unless
that is intended.

## Restart

Restarting the **API** drops the in-memory alert queue and delivery history.

```bash
docker compose restart api
docker compose restart dashboard
docker compose restart
curl -fsS http://127.0.0.1:18081/health
```

Wait until both services show `(healthy)`.

## Upgrade

1. Backup SQLite ([backup.md](backup.md)).
2. `git pull` (when the tree is committed) or copy the new tree.
3. Review `.env.production.example` for new variables.
4. `docker compose up -d --build`
5. Confirm `/health` `version` is the expected string.
6. Log in once; agents reconnect on their next outbound report.

## Backup

```bash
DB="$(docker volume inspect homelab-monitor_homelab-data --format '{{.Mountpoint}}')/homelab-monitor.db"
LOG="$(docker volume inspect homelab-monitor_homelab-logs --format '{{.Mountpoint}}')"
sudo HOMELAB_BACKUP_DB="$DB" HOMELAB_BACKUP_LOG_DIR="$LOG" ./scripts/backup.sh
./scripts/verify-backup.sh backups/<stamp>
./scripts/rotate-backups.sh
```

## Restore

```bash
docker compose stop api
./scripts/verify-backup.sh backups/<stamp>
sudo HOMELAB_BACKUP_DB="$DB" ./scripts/restore.sh backups/<stamp>
docker compose start api
curl -fsS http://127.0.0.1:18081/health
```

## Telegram

1. BotFather token + chat ID in `.env`.
2. `HOMELAB_TELEGRAM_ENABLED=true` (Compose default).
3. `docker compose up -d api` to reload env.
4. Settings → Test Message (admin).
5. Set `HOMELAB_DASHBOARD_HEALTH_URL` to the Tailscale HTTPS origin (not
   `http://dashboard:8080`) so report buttons open in a browser.

Empty token/chat: Telegram stays enabled in config but sends nothing.

## Tailscale

```bash
docker compose -f docker-compose.yml -f docker-compose.tailscale.yml up -d
sudo tailscale serve --bg 18081
sudo tailscale serve status
```

Do **not** run Funnel. Do **not** port-forward 18081 on the router. Phones must
join the tailnet.

## Photo Monitor

- Host folders must exist and match Compose `:ro` mounts.
- Poll interval default 5s (CIFS; not inotify).
- Independent of infrastructure mock.
- Telegram photos need Telegram configured.

## Immich

- **Mock ON:** Photo Services tiles are synthetic.
- **Mock OFF:** set `HOMELAB_IMMICH_URL` and `HOMELAB_IMMICH_API_KEY`, then
  `HOMELAB_INFRASTRUCTURE_MOCK=false` and recreate the API container.
- Connector is GET-only.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| API exits at start | Production bootstrap admin password missing or is `admin123` |
| Cannot log in | JWT secret changed; or user never bootstrapped |
| No Telegram | Token, chat ID, enabled flag, worker; history empty after API restart |
| Fake Immich/QNAP | Mock still `true` |
| Photo events empty | CIFS mount missing or empty; watcher disabled |
| Dashboard check unknown | Set a reachable `HOMELAB_DASHBOARD_HEALTH_URL` |
| Health 503 | Volume permissions; watch API logs; `alembic` in entrypoint |
| PWA stale | Hard refresh; `sw.js` is no-store; rebuild dashboard image |
| Tailscale 502 | Serve target must be `http://127.0.0.1:18081`; dashboard healthy |

Logs: `docker compose logs -f api dashboard`.

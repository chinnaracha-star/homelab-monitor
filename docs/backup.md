# Backup and restore

Scripts live in `scripts/`. They copy SQLite, logs, and configuration. They do
not dump running container filesystems.

## Backup

```bash
./scripts/backup.sh
```

The script prints the backup directory (`backups/<UTC-stamp>/` by default).

Layout:

```text
<stamp>/
  MANIFEST
  sqlite/homelab-monitor.db
  logs/logs.tar.gz
  config/config.tar.gz
```

SQLite is copied with `sqlite3 .backup` when `sqlite3` is installed so WAL
mode does not leave a torn file. Otherwise the `.db` (and WAL/SHM if present)
is copied.

Override paths:

| Variable | Meaning |
| --- | --- |
| `HOMELAB_BACKUP_DIR` | Parent directory for timestamped backups |
| `HOMELAB_BACKUP_DB` | Path to `homelab-monitor.db` |
| `HOMELAB_BACKUP_LOG_DIR` | Directory to archive as logs |
| `HOMELAB_BACKUP_CONFIG` | Newline-separated extra config paths |

Docker volumes can be copied from the host after locating the volume mount, or
by running the script inside a helper container that mounts `homelab-data` and
`homelab-logs`.

Example from the Compose host:

```bash
DB="$(docker volume inspect homelab-monitor_homelab-data --format '{{.Mountpoint}}')/homelab-monitor.db"
LOG="$(docker volume inspect homelab-monitor_homelab-logs --format '{{.Mountpoint}}')"
sudo HOMELAB_BACKUP_DB="$DB" HOMELAB_BACKUP_LOG_DIR="$LOG" ./scripts/backup.sh
```

## Restore

Stop the API first so SQLite is not rewritten during the copy.

```bash
docker compose stop api
# or: sudo systemctl stop homelab-monitor-api.service

./scripts/restore.sh backups/20260101T000000Z

docker compose start api
```

`HOMELAB_BACKUP_DB` and `HOMELAB_BACKUP_LOG_DIR` select restore destinations.
Set `HOMELAB_RESTORE_CONFIG_DIR` to unpack `config.tar.gz` automatically.

After restore, start the API so Alembic can apply any newer revisions
(`alembic upgrade head` runs in the API entrypoint).

# Backup

HomeLab Monitor treats a secondary QNAP **TS-253 Pro** as a read-only backup
target. The dashboard never starts, stops, deletes, moves, or uploads backup
jobs. Hybrid Backup / replication status is observed through `BackupConnector`
behind `InfrastructureService`.

```text
Phone → Qfile Pro → QNAP TS-453Be → Shared Folder → Immich / QuMagie
InfrastructureService → Backup (TS-253 Pro) → GET /api/v1/backup → Dashboard
```

`GET /api/v1/backup` requires a dashboard JWT (admin, operator, viewer). Mock
mode is the default and shows a TS-253 Pro job with Healthy status, Last Backup
02:00, 18 minute duration, ~1.8 TB size, Running 43% progress, and Backup
History (Yesterday Success, Today Running, Last Week Failed). Live mode issues
GET `{HOMELAB_BACKUP_URL}/api/backup/status` only and records snapshots for
history windows.

Realtime uses existing `overview_updated` with `reason=backup_updated`.

# Backup and restore (application data)

Scripts live in `scripts/`. They copy SQLite, logs, and non-secret configuration
examples. They do not dump running container filesystems and they do **not**
archive a live `.env`.

| Script | Role |
| --- | --- |
| `scripts/backup.sh` | Create a timestamped backup |
| `scripts/verify-backup.sh` | Checksums + `PRAGMA integrity_check` |
| `scripts/restore.sh` | Restore SQLite (stop the API first) |
| `scripts/rotate-backups.sh` | Delete backups older than N days |

## Backup

```bash
./scripts/backup.sh
```

The script prints the backup directory (`backups/<UTC-stamp>/` by default).

Layout:

```text
<stamp>/
  MANIFEST
  SHA256SUMS
  sqlite/homelab-monitor.db
  logs/logs.tar.gz
  config/config.tar.gz
```

SQLite is copied with `sqlite3 .backup` when `sqlite3` is installed so WAL
mode does not leave a torn file. The copy is then checked with
`PRAGMA integrity_check`.

| Variable | Meaning |
| --- | --- |
| `HOMELAB_BACKUP_DIR` | Parent directory for timestamped backups |
| `HOMELAB_BACKUP_DB` | Path to `homelab-monitor.db` |
| `HOMELAB_BACKUP_LOG_DIR` | Directory to archive as logs |
| `HOMELAB_BACKUP_CONFIG` | Newline-separated extra config paths |
| `HOMELAB_BACKUP_KEEP_DAYS` | Retention for `rotate-backups.sh` (default 14) |

Example from the Compose host:

```bash
DB="$(docker volume inspect homelab-monitor_homelab-data --format '{{.Mountpoint}}')/homelab-monitor.db"
LOG="$(docker volume inspect homelab-monitor_homelab-logs --format '{{.Mountpoint}}')"
sudo HOMELAB_BACKUP_DB="$DB" HOMELAB_BACKUP_LOG_DIR="$LOG" ./scripts/backup.sh
```

Daily cron example:

```bash
0 3 * * * /opt/homelab-monitor/scripts/backup.sh && /opt/homelab-monitor/scripts/rotate-backups.sh
```

## Verification

```bash
./scripts/verify-backup.sh backups/20260101T000000Z
```

Expect `ok` plus `sha256sum: OK` when `SHA256SUMS` is present. Do not restore a
directory that fails this check.

## Restore

Stop the API first so SQLite is not rewritten during the copy.

```bash
docker compose stop api
./scripts/verify-backup.sh backups/20260101T000000Z
./scripts/restore.sh backups/20260101T000000Z
docker compose start api
curl -fsS http://127.0.0.1:18081/health
```

`HOMELAB_BACKUP_DB` and `HOMELAB_BACKUP_LOG_DIR` select restore destinations.
Set `HOMELAB_RESTORE_CONFIG_DIR` to unpack `config.tar.gz`. Restore removes
sidecar `-wal`/`-shm` next to the destination database so SQLite does not mix
an old WAL with a restored file.

After start, Alembic applies any newer revisions (`alembic upgrade head` in
the API entrypoint). Confirm dashboard login and Photo Monitor events.

## Rotation

```bash
HOMELAB_BACKUP_KEEP_DAYS=14 ./scripts/rotate-backups.sh
```

Only directories named `YYYYMMDDTHHMMSSZ` that contain `MANIFEST` are removed.
Keep copies off-host (NAS share) if the Ubuntu disk is the only copy.

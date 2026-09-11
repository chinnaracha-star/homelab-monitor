#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" == "" ]]; then
  echo "usage: $0 /path/to/backup-directory" >&2
  exit 1
fi

SOURCE="$(cd "$1" && pwd)"

if [[ ! -f "$SOURCE/MANIFEST" ]]; then
  echo "error: $SOURCE is not a HomeLab Monitor backup directory" >&2
  exit 1
fi

if [[ -f "$SOURCE/SHA256SUMS" ]] && command -v sha256sum >/dev/null 2>&1; then
  (cd "$SOURCE" && sha256sum -c SHA256SUMS)
else
  echo "warning: no SHA256SUMS to verify" >&2
fi

DB="$SOURCE/sqlite/homelab-monitor.db"
if [[ -f "$DB" ]] && command -v sqlite3 >/dev/null 2>&1; then
  check="$(sqlite3 "$DB" "PRAGMA integrity_check;")"
  if [[ "$check" != "ok" ]]; then
    echo "error: SQLite integrity_check failed: $check" >&2
    exit 1
  fi
elif [[ ! -f "$DB" ]]; then
  echo "warning: backup has no SQLite database" >&2
fi

echo "ok $SOURCE"

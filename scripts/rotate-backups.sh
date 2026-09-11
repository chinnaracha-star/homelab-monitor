#!/usr/bin/env bash
# Delete timestamped backup directories older than HOMELAB_BACKUP_KEEP_DAYS (default 14).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_ROOT="${HOMELAB_BACKUP_DIR:-$ROOT_DIR/backups}"
KEEP_DAYS="${HOMELAB_BACKUP_KEEP_DAYS:-14}"

if [[ ! "$KEEP_DAYS" =~ ^[0-9]+$ ]] || ((KEEP_DAYS < 1)); then
  echo "error: HOMELAB_BACKUP_KEEP_DAYS must be a positive integer" >&2
  exit 1
fi

if [[ ! -d "$BACKUP_ROOT" ]]; then
  echo "no backup directory: $BACKUP_ROOT"
  exit 0
fi

deleted=0
now="$(date -u +%s)"
cutoff=$((KEEP_DAYS * 86400))

for dir in "$BACKUP_ROOT"/*; do
  [[ -d "$dir" ]] || continue
  [[ -f "$dir/MANIFEST" ]] || continue
  stamp="$(basename "$dir")"
  if [[ ! "$stamp" =~ ^[0-9]{8}T[0-9]{6}Z$ ]]; then
    continue
  fi
  epoch="$(date -u -d "${stamp:0:8} ${stamp:9:2}:${stamp:11:2}:${stamp:13:2}" +%s 2>/dev/null || true)"
  if [[ -z "$epoch" ]]; then
    continue
  fi
  age=$((now - epoch))
  if ((age > cutoff)); then
    rm -rf -- "$dir"
    deleted=$((deleted + 1))
  fi
done

echo "rotated $deleted directories under $BACKUP_ROOT (keep ${KEEP_DAYS}d)"

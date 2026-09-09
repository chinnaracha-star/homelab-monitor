#!/usr/bin/env bash
set -euo pipefail

PHOTO_PATHS=(
  /mnt/qnap-pictures-ss22
  /mnt/qnap-pictures-ae
)

COUNT=$(find "${PHOTO_PATHS[@]}" -path '*/@Recycle/*' -prune -o -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.heic' -o -iname '*.webp' -o -iname '*.gif' \) -print | wc -l)

SIZE=$(find "${PHOTO_PATHS[@]}" -path '*/@Recycle/*' -prune -o -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' -o -iname '*.heic' -o -iname '*.webp' -o -iname '*.gif' \) -printf '%s\n' | awk '{s+=$1} END {print s+0}')

docker exec homelab-monitor-api-1 python -c "
import sqlite3, json, uuid
from datetime import datetime, UTC

count = int('$COUNT')
size = int('$SIZE')

db = '/var/lib/homelab-monitor/homelab-monitor.db'
conn = sqlite3.connect(db)

payload = {
    'indexed_photos': count,
    'storage_used': size,
    'capacity_bytes': 12000000000000
}

observed_at = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S.%f')

conn.execute(
    'INSERT INTO ops_snapshots (id, kind, observed_at, payload) VALUES (?, ?, ?, ?)',
    (str(uuid.uuid4()), 'photo', observed_at, json.dumps(payload))
)

conn.commit()
print('photo snapshot inserted:', observed_at, payload)
"

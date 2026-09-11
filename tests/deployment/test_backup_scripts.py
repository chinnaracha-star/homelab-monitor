from __future__ import annotations

import os
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_backup_verify_restore_roundtrip(tmp_path: Path) -> None:
    db = tmp_path / "homelab-monitor.db"
    sqlite3.connect(db).execute("CREATE TABLE ping (id INTEGER PRIMARY KEY)").connection.commit()
    log_dir = tmp_path / "src-logs"
    log_dir.mkdir()
    (log_dir / "api.jsonl").write_text("{}\n", encoding="utf-8")

    backup_root = tmp_path / "backups"
    env = os.environ.copy()
    env.update(
        {
            "HOMELAB_BACKUP_DIR": str(backup_root),
            "HOMELAB_BACKUP_DB": str(db),
            "HOMELAB_BACKUP_LOG_DIR": str(log_dir),
            "HOMELAB_BACKUP_CONFIG": str(ROOT / ".env.example"),
        }
    )
    dest = subprocess.check_output(
        [str(ROOT / "scripts" / "backup.sh")],
        env=env,
        text=True,
    ).strip()

    assert (Path(dest) / "MANIFEST").is_file()
    subprocess.check_call([str(ROOT / "scripts" / "verify-backup.sh"), dest])

    restored = tmp_path / "restored.db"
    restore_env = os.environ.copy()
    restore_env.update(
        {
            "HOMELAB_BACKUP_DB": str(restored),
            "HOMELAB_BACKUP_LOG_DIR": str(tmp_path / "out-logs"),
        }
    )
    subprocess.check_call([str(ROOT / "scripts" / "restore.sh"), dest], env=restore_env)
    conn = sqlite3.connect(restored)
    assert conn.execute("SELECT name FROM sqlite_master WHERE name='ping'").fetchone()

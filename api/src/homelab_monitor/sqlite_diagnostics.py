"""Process-local notes about who is writing SQLite. Does not retry or commit."""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

logger = logging.getLogger("homelab_monitor.sqlite_diagnostics")

_lock = threading.Lock()
_seq = 0
_active: dict[int, tuple[str, float]] = {}

_KINDS = ("INSERT", "UPDATE", "DELETE", "SELECT")
_TABLES = (
    "agents",
    "alerts",
    "photo_events",
    "notifications",
    "ops_snapshots",
    "metric_reports",
    "notification_settings",
)


@contextmanager
def writer_operation(name: str) -> Iterator[None]:
    """Mark one DB write section. The mark ends on return or any exception."""
    global _seq
    with _lock:
        _seq += 1
        token = _seq
        _active[token] = (name, time.monotonic())
    try:
        yield
    finally:
        with _lock:
            _active.pop(token, None)


def active_writers() -> list[dict[str, object]]:
    now = time.monotonic()
    with _lock:
        items = list(_active.values())
    return [
        {"operation": name, "elapsed_ms": round((now - started) * 1000, 1)}
        for name, started in items
    ]


def is_database_locked(error: OperationalError) -> bool:
    text = str(getattr(error, "orig", error))
    return "database is locked" in text.lower()


def classify_statement(statement: object) -> tuple[str, str]:
    if not isinstance(statement, str) or not statement.strip():
        return "UNKNOWN", "unknown"
    head = statement.lstrip().split(None, 1)[0].upper()
    kind = head if head in _KINDS else "UNKNOWN"
    folded = statement.upper()
    for table in _TABLES:
        if table.upper() in folded:
            return kind, table
    return kind, "unknown"


def log_sqlite_busy(
    error: OperationalError,
    *,
    operation: str,
    session: Session | None,
    started: float,
) -> None:
    """Log a lock without the SQL parameters, then return. Caller re-raises."""
    kind, target = classify_statement(getattr(error, "statement", None))
    writers = active_writers()
    logger.warning(
        "sqlite_busy_detected operation=%s statement_kind=%s target=%s "
        "transaction_active=%s transaction_nested=%s session=%s elapsed_ms=%s "
        "active_writers=%s",
        operation,
        kind,
        target,
        bool(session.in_transaction()) if session is not None else "unknown",
        bool(session.in_nested_transaction()) if session is not None else "unknown",
        id(session) if session is not None else "none",
        round((time.monotonic() - started) * 1000, 1),
        writers,
    )

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from homelab_monitor.alert_history import list_alert_history
from homelab_monitor.alert_severity import (
    CRITICAL,
    WARNING,
    alert_payload_severity,
    telegram_alert_line,
)
from homelab_monitor.analytics import AnalyticsService
from homelab_monitor.capacity_planning import CapacityPlanningService, _bytes_label
from homelab_monitor.database import get_engine
from homelab_monitor.history import as_utc
from homelab_monitor.insights import InsightService
from homelab_monitor.models import Notification
from homelab_monitor.notifications.config import load_payload, save_payload
from homelab_monitor.notifications.dispatcher import dispatch_telegram_report
from homelab_monitor.ops_history import _status_from_payload
from homelab_monitor.settings import Settings
from homelab_monitor.trends import TrendService

logger = logging.getLogger("homelab_monitor.telegram_reports")

DEFAULT_REPORTS = {
    "hourly_enabled": False,
    "daily_enabled": False,
    "weekly_enabled": False,
    "hour_interval": 1,
    "daily_time": "08:00",
    "weekly_day": "sunday",
    "weekly_time": "08:00",
    "timezone": "Asia/Bangkok",
    "last_sent": {},
}
WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
MONTHS = (
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
TICK_SECONDS = 60


def reports_payload(payload: dict) -> dict:
    stored = payload.get("reports")
    merged = dict(DEFAULT_REPORTS)
    if isinstance(stored, dict):
        merged.update({key: stored[key] for key in stored if key in merged or key == "last_sent"})
        last_sent = stored.get("last_sent")
        merged["last_sent"] = dict(last_sent) if isinstance(last_sent, dict) else {}
    interval = int(merged.get("hour_interval") or 1)
    merged["hour_interval"] = min(24, max(1, interval))
    return merged


def report_timezone(name: str) -> tzinfo:
    try:
        return ZoneInfo(name or "Asia/Bangkok")
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=7))


def _parse_time(value: str) -> tuple[int, int]:
    try:
        hour_text, minute_text = (value or "08:00").split(":", 1)
        hour = min(23, max(0, int(hour_text)))
        minute = min(59, max(0, int(minute_text)))
        return hour, minute
    except (TypeError, ValueError):
        return 8, 0


def _parse_sent(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return as_utc(parsed)


def _english_date(local: datetime) -> str:
    return f"{local.day} {MONTHS[local.month]} {local.year}"


def _pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{round(value)}%"


def _num(value: float | None) -> str:
    if value is None:
        return "—"
    return str(round(value, 2) if isinstance(value, float) else value)


def _agent_line(overview) -> str:
    agents = overview.daily
    if agents.agents_total == 0:
        return "Unknown"
    if agents.agents_online == agents.agents_total:
        return "Online"
    if agents.agents_online == 0:
        return "Offline"
    return f"{agents.agents_online}/{agents.agents_total} Online"


def _agent_badge(overview) -> str:
    line = _agent_line(overview)
    if line == "Offline":
        return f"🔴 {line}"
    if line == "Unknown":
        return f"⚪ {line}"
    return f"🟢 {line}"


def _agent_emoji(overview) -> str:
    return _agent_badge(overview).split(" ", 1)[0]


def _hourly_alert_section(alerts: list) -> list[str]:
    ranked: list[tuple[str, object]] = []
    for item in alerts:
        severity = alert_payload_severity(item.alert_type, item.peak_value, item.severity)
        if severity in {WARNING, CRITICAL}:
            ranked.append((severity, item))
    warnings = [item for severity, item in ranked if severity == WARNING]
    criticals = [item for severity, item in ranked if severity == CRITICAL]
    if not warnings and not criticals:
        return ["✅ Everything looks healthy."]
    lines: list[str] = []
    if warnings:
        lines.append("⚠ Warning")
        lines.extend(
            f"• {telegram_alert_line(item.alert_type, WARNING, item.peak_value)}"
            for item in warnings
        )
    if criticals:
        if lines:
            lines.append("")
        lines.append("🚨 Critical")
        lines.extend(
            f"• {telegram_alert_line(item.alert_type, CRITICAL, item.peak_value)}"
            for item in criticals
        )
    return lines


def _actionable_alert_count(alerts: list) -> int:
    return sum(
        1
        for item in alerts
        if alert_payload_severity(item.alert_type, item.peak_value, item.severity)
        in {WARNING, CRITICAL}
    )


def next_hourly(local: datetime, interval: int) -> datetime:
    aligned_hour = (local.hour // interval) * interval
    slot = local.replace(hour=aligned_hour, minute=0, second=0, microsecond=0)
    if local >= slot:
        slot = slot + timedelta(hours=interval)
    return slot


def next_daily(local: datetime, hour: int, minute: int) -> datetime:
    slot = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if local >= slot:
        slot = slot + timedelta(days=1)
    return slot


def next_weekly(local: datetime, weekday: int, hour: int, minute: int) -> datetime:
    slot = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    days_ahead = (weekday - slot.weekday()) % 7
    if days_ahead == 0 and local >= slot:
        days_ahead = 7
    return slot + timedelta(days=days_ahead)


def due_hourly(local: datetime, last: datetime | None, interval: int) -> bool:
    aligned_hour = (local.hour // interval) * interval
    slot = local.replace(hour=aligned_hour, minute=0, second=0, microsecond=0)
    if last is None:
        return True
    return as_utc(last) < slot.astimezone(UTC)


def due_daily(local: datetime, last: datetime | None, hour: int, minute: int) -> bool:
    slot = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if local < slot:
        return False
    if last is None:
        return True
    return as_utc(last).astimezone(slot.tzinfo).date() < local.date()


def due_weekly(
    local: datetime,
    last: datetime | None,
    weekday: int,
    hour: int,
    minute: int,
) -> bool:
    if local.weekday() != weekday:
        return False
    return due_daily(local, last, hour, minute)


class TelegramReportService:
    def __init__(
        self,
        analytics: AnalyticsService | None = None,
        trends: TrendService | None = None,
        capacity: CapacityPlanningService | None = None,
        insights: InsightService | None = None,
    ) -> None:
        self.analytics = analytics or AnalyticsService()
        self.trends = trends or TrendService(analytics=self.analytics)
        self.capacity = capacity or CapacityPlanningService(
            analytics=self.analytics, trends=self.trends
        )
        self.insights = insights or InsightService(
            analytics=self.analytics, trends=self.trends, capacity=self.capacity
        )

    def build(self, db: Session, kind: str, *, now: datetime | None = None) -> str:
        clock = now or datetime.now(UTC)
        if kind == "daily_report":
            return self._daily(db, clock)
        if kind == "weekly_report":
            return self._weekly(db, clock)
        if kind == "test_report":
            return self.build_test_report(db, now=clock)
        return self._hourly(db, clock)

    def _snapshot(self, db: Session, now: datetime) -> dict:
        overview = self.analytics.overview(db, now=now)
        cpu = self.analytics.cpu(db, now=now)
        memory = self.analytics.memory(db, now=now)
        temperature = self.analytics.temperature(db, now=now)
        photos = self.analytics.photos(db, now=now)
        backup = self.analytics.backup(db, now=now)
        storage = self.trends.storage(db, now=now)
        system = self.capacity.system(db, now=now)
        snapshots = self.analytics.backup_snapshots(db)
        latest_backup = snapshots[-1] if snapshots else None
        backup_status = "Unknown"
        if latest_backup is not None:
            status = _status_from_payload(latest_backup.payload)
            backup_status = "Success" if status == "success" else status.title()
        alerts = list_alert_history(db, status="active", now=now)
        return {
            "overview": overview,
            "cpu": cpu,
            "memory": memory,
            "temperature": temperature,
            "photos": photos,
            "backup": backup,
            "storage": storage,
            "score": system.overall_score,
            "backup_status": backup_status,
            "alerts": alerts,
        }

    def _hourly(self, db: Session, now: datetime) -> str:
        data = self._snapshot(db, now)
        tz = report_timezone(str(reports_payload(load_payload(db))["timezone"]))
        local = now.astimezone(tz)
        used = data["storage"].current_used
        _, detail, _ = self.analytics.photo_detail(db, now=now)
        capacity = int(detail.get("capacity") or 0)
        storage_lines = [_pct(data["storage"].used_percent)]
        if used or capacity:
            storage_lines.append(f"({_bytes_label(float(used))} / {_bytes_label(float(capacity))})")
        alerts = data["alerts"]
        lines = [
            "🏠 HomeLab Hourly Report",
            "",
            f"🕓 {local.strftime('%H:%M')}",
            "",
            "━━━━━━━━━━━━━━",
            "",
            f"{_agent_emoji(data['overview'])} Agent",
            _agent_line(data["overview"]),
            "",
            "🖥 CPU",
            _pct(data["cpu"].current),
            "",
            "🧠 Memory",
            _pct(data["memory"].current),
            "",
            "💾 Storage",
            *storage_lines,
            "",
            "🌡 Temperature",
            f"{_num(data['temperature'].current)}°C",
            "",
            "📷 Photos Today",
            f"+{data['photos'].today}",
            "",
            "💾 Last Backup",
            data["backup_status"],
            "",
            "⚠ Active Alerts",
            str(_actionable_alert_count(alerts)),
            "",
            "📊 Health Score",
            f"{round(data['score'])} / 100",
            "",
            "━━━━━━━━━━━━━━",
            "",
        ]
        lines.extend(_hourly_alert_section(alerts))
        return "\n".join(lines)

    def build_test_report(self, db: Session, *, now: datetime | None = None) -> str:
        clock = now or datetime.now(UTC)
        data = self._snapshot(db, clock)
        tz = report_timezone(str(reports_payload(load_payload(db))["timezone"]))
        local = clock.astimezone(tz)
        footer = (
            "✅ Everything looks healthy."
            if not data["alerts"]
            else "Active alerts are listed in the live dashboard."
        )
        return "\n".join(
            [
                "🏠 HomeLab Test Report",
                "━━━━━━━━━━━━━━━━",
                "✅ Status: Telegram connected",
                f"🕒 Time: {_english_date(local)} {local.strftime('%H:%M:%S')}",
                "━━━━━━━━━━━━━━━━",
                "",
                "📡 Agent",
                f"• Status: {_agent_badge(data['overview'])}",
                "",
                "📊 System Metrics",
                f"• ⚙️ CPU: {_pct(data['cpu'].current)}",
                f"• 🧠 Memory: {_pct(data['memory'].current)}",
                f"• 💾 Storage: {_pct(data['storage'].used_percent)}",
                f"• 🌡 Temperature: {_num(data['temperature'].current)}°C",
                "",
                "❤️ Health",
                f"• Score: {round(data['score'])} / 100",
                f"• Result: {footer}",
                "",
                "━━━━━━━━━━━━━━━━",
                "Settings → Send Test Report",
            ]
        )

    def _daily(self, db: Session, now: datetime) -> str:
        data = self._snapshot(db, now)
        local = now.astimezone(timezone(timedelta(hours=7)))
        start_today = now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = [
            item
            for item in list_alert_history(db, now=now)
            if item.started_at is not None
            and start_today - timedelta(days=1) <= as_utc(item.started_at) < start_today
        ]
        recommendation = self.insights.overview(db).recommendation or (
            "Everything is operating normally."
        )
        footer = "Everything is operating normally." if not yesterday else recommendation
        return "\n".join(
            [
                "🌅 HomeLab Daily Report",
                "",
                "Date",
                "",
                _english_date(local),
                "",
                "━━━━━━━━━━━━━━",
                "",
                "CPU Average",
                _pct(data["overview"].cpu_average),
                "",
                "Memory Average",
                _pct(data["overview"].memory_average),
                "",
                "Temperature Average",
                f"{_num(data['overview'].temperature_average)}°C",
                "",
                "Storage Growth",
                _bytes_label(float(data["storage"].daily_growth_bytes)),
                "",
                "Photo Growth",
                f"+{data['photos'].today}",
                "",
                "Backup Success Rate",
                _pct(data["backup"].success_rate),
                "",
                "Photos Today",
                str(data["photos"].today),
                "",
                "Alerts Yesterday",
                str(len(yesterday)),
                "",
                "Current Health Score",
                f"{round(data['score'])} / 100",
                "",
                "Top Recommendation",
                recommendation,
                "",
                "━━━━━━━━━━━━━━",
                "",
                footer,
            ]
        )

    def _weekly(self, db: Session, now: datetime) -> str:
        data = self._snapshot(db, now)
        week_ago = now - timedelta(days=7)
        history = list_alert_history(db, now=now)
        week_alerts = [item for item in history if as_utc(item.started_at) >= week_ago]
        recovered = [item for item in week_alerts if item.status == "recovered"]
        cpu_trend = self.trends.cpu(db, now=now)
        memory_trend = self.trends.memory(db, now=now)
        capacity = self.capacity.storage(db, now=now)
        insight = self.insights.overview(db)
        days = capacity.estimated_days_remaining
        if days is None:
            forecast = "Capacity forecast is unknown."
        else:
            forecast = f"Estimated capacity remaining {days} days."
        recommendation = insight.recommendation or "No critical issues detected."
        return "\n".join(
            [
                "📅 HomeLab Weekly Report",
                "",
                "Week Summary",
                "",
                "━━━━━━━━━━━━━━",
                "",
                "Average CPU",
                _pct(cpu_trend.average_7d),
                "",
                "Average Memory",
                _pct(memory_trend.average_7d),
                "",
                "Storage Growth",
                _bytes_label(float(data["storage"].weekly_growth_bytes)),
                "",
                "Photo Growth",
                f"+{data['photos'].this_week}",
                "",
                "Backup Success",
                _pct(data["backup"].success_rate),
                "",
                "Total Alerts",
                str(len(week_alerts)),
                "",
                "Recovered Alerts",
                str(len(recovered)),
                "",
                "Health Score",
                f"{round(data['score'])} / 100",
                "",
                "Top Recommendation",
                recommendation,
                "",
                "Capacity Forecast",
                forecast,
                "",
                "━━━━━━━━━━━━━━",
                "",
                "No critical issues detected."
                if insight.severity in {"info", "healthy", "unknown", ""}
                else recommendation,
            ]
        )


def send_manual_test_report(
    db: Session,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> Notification:
    message = TelegramReportService().build_test_report(db, now=now)
    return dispatch_telegram_report(db, settings, kind="test_report", message=message)


def public_reports(payload: dict, *, now: datetime | None = None) -> dict:
    reports = reports_payload(payload)
    clock = now or datetime.now(UTC)
    tz = report_timezone(str(reports["timezone"]))
    local = clock.astimezone(tz)
    interval = int(reports["hour_interval"])
    daily_hour, daily_minute = _parse_time(str(reports["daily_time"]))
    weekly_hour, weekly_time = _parse_time(str(reports["weekly_time"]))
    weekday = WEEKDAYS.get(str(reports["weekly_day"]).lower(), 6)
    last_sent = reports.get("last_sent") if isinstance(reports.get("last_sent"), dict) else {}
    cards = {
        "hourly": {
            "enabled": bool(reports["hourly_enabled"]),
            "last_sent": _parse_sent(last_sent.get("hourly_report")),
            "next_scheduled": next_hourly(local, interval).isoformat(),
            "status": "enabled" if reports["hourly_enabled"] else "disabled",
        },
        "daily": {
            "enabled": bool(reports["daily_enabled"]),
            "last_sent": _parse_sent(last_sent.get("daily_report")),
            "next_scheduled": next_daily(local, daily_hour, daily_minute).isoformat(),
            "status": "enabled" if reports["daily_enabled"] else "disabled",
        },
        "weekly": {
            "enabled": bool(reports["weekly_enabled"]),
            "last_sent": _parse_sent(last_sent.get("weekly_report")),
            "next_scheduled": next_weekly(local, weekday, weekly_hour, weekly_time).isoformat(),
            "status": "enabled" if reports["weekly_enabled"] else "disabled",
        },
    }
    return {
        "hourly_enabled": bool(reports["hourly_enabled"]),
        "daily_enabled": bool(reports["daily_enabled"]),
        "weekly_enabled": bool(reports["weekly_enabled"]),
        "hour_interval": interval,
        "daily_time": str(reports["daily_time"]),
        "weekly_day": str(reports["weekly_day"]),
        "weekly_time": str(reports["weekly_time"]),
        "timezone": str(reports["timezone"]),
        **cards,
    }


def _mark_sent(payload: dict, kind: str, when: datetime) -> dict:
    reports = reports_payload(payload)
    last_sent = dict(reports.get("last_sent") or {})
    last_sent[kind] = as_utc(when).isoformat()
    reports["last_sent"] = last_sent
    next_payload = dict(payload)
    next_payload["reports"] = reports
    return next_payload


def process_due_reports(
    db: Session,
    settings: Settings,
    *,
    now: datetime | None = None,
    service: TelegramReportService | None = None,
) -> list[Notification]:
    clock = now or datetime.now(UTC)
    payload = load_payload(db)
    reports = reports_payload(payload)
    tz = report_timezone(str(reports["timezone"]))
    local = clock.astimezone(tz)
    last_sent = reports.get("last_sent") if isinstance(reports.get("last_sent"), dict) else {}
    interval = int(reports["hour_interval"])
    daily_hour, daily_minute = _parse_time(str(reports["daily_time"]))
    weekly_hour, weekly_minute = _parse_time(str(reports["weekly_time"]))
    weekday = WEEKDAYS.get(str(reports["weekly_day"]).lower(), 6)
    builder = service or TelegramReportService()
    due: list[tuple[str, bool]] = []
    if due_hourly(local, _parse_sent(last_sent.get("hourly_report")), interval):
        due.append(("hourly_report", bool(reports["hourly_enabled"])))
    if due_daily(local, _parse_sent(last_sent.get("daily_report")), daily_hour, daily_minute):
        due.append(("daily_report", bool(reports["daily_enabled"])))
    if due_weekly(
        local, _parse_sent(last_sent.get("weekly_report")), weekday, weekly_hour, weekly_minute
    ):
        due.append(("weekly_report", bool(reports["weekly_enabled"])))
    rows: list[Notification] = []
    for kind, enabled in due:
        if not enabled:
            continue
        message = builder.build(db, kind, now=clock)
        row = dispatch_telegram_report(db, settings, kind=kind, message=message)
        if row is not None:
            rows.append(row)
        payload = _mark_sent(payload, kind, clock)
        save_payload(db, payload)
    return rows


def tick_telegram_reports(settings: Settings, *, now: datetime | None = None) -> None:
    with Session(get_engine()) as db:
        process_due_reports(db, settings, now=now)


async def run_telegram_reports(settings: Settings) -> None:
    while True:
        await asyncio.sleep(TICK_SECONDS)
        try:
            await asyncio.to_thread(tick_telegram_reports, settings)
        except SQLAlchemyError:
            logger.exception("telegram_report_tick_failed")

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from homelab_monitor.models import Agent, Alert
from homelab_monitor.settings import Settings

logger = logging.getLogger("homelab_monitor.alerts")


@dataclass(frozen=True)
class AlertEvent:
    agent_id: str
    agent_name: str
    kind: str
    resource: str
    value: float
    threshold: float
    message: str
    observed_at: datetime


class AlertEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate_report(
        self,
        db: Session,
        agent: Agent,
        payload: dict[str, Any],
        observed_at: datetime,
    ) -> list[AlertEvent]:
        events: list[AlertEvent] = []
        for module in payload.get("modules", []):
            if module.get("module") != "system":
                continue
            metrics = module.get("metrics", {})
            events.extend(self._evaluate_system_metrics(db, agent, metrics, observed_at))
        return events

    def mark_agent_online(self, db: Session, agent: Agent, observed_at: datetime) -> None:
        self._set_threshold_state(
            db,
            agent,
            kind="agent_offline",
            resource="agent",
            value=0,
            threshold=float(self.settings.agent_offline_after_seconds),
            breached=False,
            observed_at=observed_at,
            message=f"Agent {agent.name} is online",
        )

    def evaluate_offline_agents(
        self,
        db: Session,
        now: datetime | None = None,
    ) -> list[AlertEvent]:
        observed_at = now or datetime.now(UTC)
        events: list[AlertEvent] = []
        for agent in db.scalars(select(Agent)).all():
            last_contact = agent.last_seen_at or agent.created_at
            if last_contact is None:
                continue
            elapsed = (observed_at - self._as_utc(last_contact)).total_seconds()
            offline = elapsed > self.settings.agent_offline_after_seconds
            if offline:
                agent.status = "offline"
            event = self._set_threshold_state(
                db,
                agent,
                kind="agent_offline",
                resource="agent",
                value=max(0, elapsed),
                threshold=float(self.settings.agent_offline_after_seconds),
                breached=offline,
                observed_at=observed_at,
                message=(
                    f"Agent {agent.name} has been offline for {int(max(0, elapsed))} seconds"
                    if offline
                    else f"Agent {agent.name} is online"
                ),
            )
            if event is not None:
                events.append(event)
        return events

    def _evaluate_system_metrics(
        self,
        db: Session,
        agent: Agent,
        metrics: dict[str, Any],
        observed_at: datetime,
    ) -> list[AlertEvent]:
        events: list[AlertEvent] = []
        cpu = self._usage_value(metrics, "cpu", "cpu_percent")
        if cpu is not None:
            event = self._evaluate_metric(
                db,
                agent,
                "cpu_high",
                "system",
                cpu,
                self.settings.alert_cpu_threshold_percent,
                observed_at,
                "CPU usage",
                "%",
            )
            if event is not None:
                events.append(event)

        memory = self._usage_value(metrics, "memory", "memory_percent")
        if memory is not None:
            event = self._evaluate_metric(
                db,
                agent,
                "memory_high",
                "system",
                memory,
                self.settings.alert_memory_threshold_percent,
                observed_at,
                "Memory usage",
                "%",
            )
            if event is not None:
                events.append(event)

        for disk in metrics.get("disks", []):
            value = self._number(disk.get("usage_percent"))
            resource = str(disk.get("mount_point") or disk.get("filesystem") or "unknown")
            if value is not None:
                event = self._evaluate_metric(
                    db,
                    agent,
                    "disk_high",
                    resource,
                    value,
                    self.settings.alert_disk_threshold_percent,
                    observed_at,
                    f"Disk usage on {resource}",
                    "%",
                )
                if event is not None:
                    events.append(event)

        for sensor in metrics.get("temperatures", []):
            value = self._number(sensor.get("current_celsius"))
            source = str(sensor.get("source") or "sensor")
            label = str(sensor.get("label") or source)
            if value is not None:
                event = self._evaluate_metric(
                    db,
                    agent,
                    "temperature_high",
                    f"{source}:{label}",
                    value,
                    self.settings.alert_temperature_threshold_celsius,
                    observed_at,
                    f"Temperature for {label}",
                    "°C",
                )
                if event is not None:
                    events.append(event)
        return events

    def _evaluate_metric(
        self,
        db: Session,
        agent: Agent,
        kind: str,
        resource: str,
        value: float,
        threshold: float,
        observed_at: datetime,
        label: str,
        unit: str,
    ) -> AlertEvent | None:
        breached = value > threshold
        relation = "exceeded" if breached else "is within"
        return self._set_threshold_state(
            db,
            agent,
            kind=kind,
            resource=resource,
            value=value,
            threshold=threshold,
            breached=breached,
            observed_at=observed_at,
            message=f"{label} {value:g}{unit} {relation} threshold {threshold:g}{unit}",
        )

    @staticmethod
    def _usage_value(
        metrics: dict[str, Any],
        nested_key: str,
        legacy_key: str,
    ) -> float | None:
        nested = metrics.get(nested_key)
        if isinstance(nested, dict):
            value = AlertEngine._number(nested.get("usage_percent"))
            if value is not None:
                return value
        return AlertEngine._number(metrics.get(legacy_key))

    @staticmethod
    def _number(value: Any) -> float | None:
        if isinstance(value, bool) or not isinstance(value, int | float):
            return None
        return float(value)

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _set_threshold_state(
        db: Session,
        agent: Agent,
        *,
        kind: str,
        resource: str,
        value: float,
        threshold: float,
        breached: bool,
        observed_at: datetime,
        message: str,
    ) -> AlertEvent | None:
        alert = db.scalar(
            select(Alert).where(
                Alert.agent_id == agent.id,
                Alert.kind == kind,
                Alert.resource == resource,
            )
        )
        if breached:
            if alert is None:
                alert = Alert(
                    agent_id=agent.id,
                    kind=kind,
                    resource=resource,
                    status="active",
                    severity="warning",
                    current_value=value,
                    threshold=threshold,
                    message=message,
                    opened_at=observed_at,
                    last_observed_at=observed_at,
                )
                db.add(alert)
                logger.warning(
                    "alert_opened",
                    extra={"agent_id": agent.id, "kind": kind, "resource": resource},
                )
                return AlertEvent(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    kind=kind,
                    resource=resource,
                    value=value,
                    threshold=threshold,
                    message=message,
                    observed_at=observed_at,
                )
            else:
                if alert.status == "resolved":
                    alert.status = "active"
                    alert.opened_at = observed_at
                    alert.resolved_at = None
                    logger.warning(
                        "alert_reopened",
                        extra={"agent_id": agent.id, "kind": kind, "resource": resource},
                    )
                    event = AlertEvent(
                        agent_id=agent.id,
                        agent_name=agent.name,
                        kind=kind,
                        resource=resource,
                        value=value,
                        threshold=threshold,
                        message=message,
                        observed_at=observed_at,
                    )
                else:
                    event = None
                alert.current_value = value
                alert.threshold = threshold
                alert.message = message
                alert.last_observed_at = observed_at
                return event

        if alert is not None and alert.status == "active":
            alert.status = "resolved"
            alert.current_value = value
            alert.threshold = threshold
            alert.message = message
            alert.last_observed_at = observed_at
            alert.resolved_at = observed_at
            logger.info(
                "alert_resolved",
                extra={"agent_id": agent.id, "kind": kind, "resource": resource},
            )
        return None

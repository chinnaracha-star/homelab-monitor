from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from homelab_monitor.auth.dependencies import require_roles
from homelab_monitor.database import get_db
from homelab_monitor.errors import APIError
from homelab_monitor.models import Agent, Alert, MetricReport
from homelab_monitor.realtime import hub
from homelab_monitor.schemas import (
    ActiveAlertResponse,
    AgentCountResponse,
    AgentDetailResponse,
    AgentSummaryResponse,
    AlertAcknowledgeResponse,
    DashboardOverviewResponse,
    LatestMetricReportResponse,
    ReportCountResponse,
)

router = APIRouter(
    prefix="/api/v1",
    tags=["dashboard"],
    dependencies=[Depends(require_roles("admin", "operator", "viewer"))],
)


@router.get(
    "/dashboard/overview",
    response_model=DashboardOverviewResponse,
    summary="Get dashboard summary counts",
)
def get_dashboard_overview(
    db: Annotated[Session, Depends(get_db)],
) -> DashboardOverviewResponse:
    total_agents = db.scalar(select(func.count()).select_from(Agent)) or 0
    online_agents = (
        db.scalar(select(func.count()).select_from(Agent).where(Agent.status == "online")) or 0
    )
    total_reports = db.scalar(select(func.count()).select_from(MetricReport)) or 0

    return DashboardOverviewResponse(
        agents=AgentCountResponse(
            total=total_agents,
            online=online_agents,
            offline=total_agents - online_agents,
        ),
        reports=ReportCountResponse(total=total_reports),
    )


@router.get(
    "/agents",
    response_model=list[AgentSummaryResponse],
    summary="List monitored agents",
)
def list_agents(db: Annotated[Session, Depends(get_db)]) -> list[Agent]:
    return list(db.scalars(select(Agent).order_by(Agent.name.asc())).all())


@router.get(
    "/agents/{agent_id}",
    response_model=AgentDetailResponse,
    summary="Get one monitored agent",
)
def get_agent(
    agent_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> AgentDetailResponse:
    agent = db.scalar(
        select(Agent).options(selectinload(Agent.configuration)).where(Agent.id == agent_id)
    )
    if agent is None:
        raise APIError(404, "agent_not_found", "The requested agent does not exist")

    return AgentDetailResponse(
        id=agent.id,
        name=agent.name,
        hostname=agent.hostname,
        version=agent.version,
        status=agent.status,
        last_seen_at=agent.last_seen_at,
        configuration_revision=agent.configuration.revision if agent.configuration else 0,
        capabilities=agent.capabilities,
    )


@router.get(
    "/agents/{agent_id}/latest-report",
    response_model=LatestMetricReportResponse,
    summary="Get the newest metric report for an agent",
)
def get_latest_agent_report(
    agent_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> MetricReport:
    if db.scalar(select(Agent.id).where(Agent.id == agent_id)) is None:
        raise APIError(404, "agent_not_found", "The requested agent does not exist")

    report = db.scalar(
        select(MetricReport)
        .where(MetricReport.agent_id == agent_id)
        .order_by(
            MetricReport.observed_at.desc(),
            MetricReport.received_at.desc(),
            MetricReport.id.desc(),
        )
        .limit(1)
    )
    if report is None:
        raise APIError(
            404,
            "latest_report_not_found",
            "The requested agent has no metric reports",
        )
    return report


@router.get(
    "/agents/{agent_id}/reports",
    response_model=list[LatestMetricReportResponse],
    summary="Get recent metric reports for an agent",
)
def get_agent_report_history(
    agent_id: str,
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=2, le=100)] = 30,
) -> list[MetricReport]:
    if db.scalar(select(Agent.id).where(Agent.id == agent_id)) is None:
        raise APIError(404, "agent_not_found", "The requested agent does not exist")

    return list(
        db.scalars(
            select(MetricReport)
            .where(MetricReport.agent_id == agent_id)
            .order_by(
                MetricReport.observed_at.desc(),
                MetricReport.received_at.desc(),
                MetricReport.id.desc(),
            )
            .limit(limit)
        ).all()
    )


@router.get(
    "/alerts/active",
    response_model=list[ActiveAlertResponse],
    summary="List active alerts",
)
def list_active_alerts(
    db: Annotated[Session, Depends(get_db)],
) -> list[ActiveAlertResponse]:
    rows = db.execute(
        select(Alert, Agent.name)
        .join(Agent, Alert.agent_id == Agent.id)
        .where(Alert.status == "active")
        .order_by(Alert.opened_at.desc(), Alert.id.desc())
    ).all()

    return [
        ActiveAlertResponse(
            id=alert.id,
            agent_id=alert.agent_id,
            agent_name=agent_name,
            kind=alert.kind,
            resource=alert.resource,
            severity=alert.severity,
            current_value=alert.current_value,
            threshold=alert.threshold,
            message=alert.message,
            opened_at=alert.opened_at,
            last_observed_at=alert.last_observed_at,
        )
        for alert, agent_name in rows
    ]


@router.post(
    "/alerts/{alert_id}/acknowledge",
    response_model=AlertAcknowledgeResponse,
    dependencies=[Depends(require_roles("admin", "operator"))],
    summary="Acknowledge an active alert",
)
def acknowledge_alert(
    alert_id: str,
    db: Annotated[Session, Depends(get_db)],
) -> Alert:
    alert = db.scalar(select(Alert).where(Alert.id == alert_id))
    if alert is None:
        raise APIError(404, "alert_not_found", "The requested alert does not exist")
    hub.publish("alert_updated", reason="acknowledge", agent_id=alert.agent_id)
    return alert

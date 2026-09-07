import hashlib
import json
import secrets
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from homelab_monitor.control import build_agent_control
from homelab_monitor.database import get_db
from homelab_monitor.errors import APIError
from homelab_monitor.models import Agent, AgentConfiguration, MetricReport
from homelab_monitor.schemas import (
    AgentCheckInRequest,
    AgentControlResponse,
    AgentRegistrationRequest,
    AgentRegistrationResponse,
    MetricReportRequest,
    MetricReportResponse,
)
from homelab_monitor.security import create_agent_token, get_current_agent, hash_agent_token
from homelab_monitor.settings import Settings, get_settings

router = APIRouter(prefix="/api/v1", tags=["agents"])


@router.post(
    "/agents/register",
    response_model=AgentRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register an agent and issue its one-time credential",
)
def register_agent(
    payload: AgentRegistrationRequest,
    registration_key: Annotated[str | None, Header(alias="X-Registration-Key")],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AgentRegistrationResponse:
    if registration_key is None or not secrets.compare_digest(
        registration_key, settings.registration_key
    ):
        raise APIError(401, "invalid_registration_key", "The registration key is invalid")

    if db.scalar(select(Agent.id).where(Agent.name == payload.name)) is not None:
        raise APIError(409, "agent_name_exists", "An agent with this name already exists")

    token = create_agent_token()
    agent = Agent(
        name=payload.name,
        hostname=payload.hostname,
        version=payload.version,
        token_hash=hash_agent_token(token),
        capabilities=sorted(set(payload.capabilities)),
    )
    agent.configuration = AgentConfiguration(revision=1, settings={})
    db.add(agent)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise APIError(
            409,
            "agent_registration_conflict",
            "Agent registration conflicted",
        ) from error
    db.refresh(agent)

    return AgentRegistrationResponse(
        agent_id=agent.id,
        agent_token=token,
        report_interval_seconds=settings.agent_report_interval_seconds,
        config_revision=agent.configuration.revision,
    )


@router.post(
    "/agent/check-ins",
    response_model=AgentControlResponse,
    summary="Record an agent heartbeat and receive server policy",
)
def check_in(
    payload: AgentCheckInRequest,
    agent: Annotated[Agent, Depends(get_current_agent)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AgentControlResponse:
    agent.version = payload.version
    agent.last_seen_at = datetime.now(UTC)
    agent.status = "online"
    db.commit()
    db.refresh(agent)
    return build_agent_control(agent, settings, payload.config_revision)


@router.post(
    "/agent/reports",
    response_model=MetricReportResponse,
    summary="Upload an idempotent batch of monitoring results",
)
def upload_report(
    payload: MetricReportRequest,
    agent: Annotated[Agent, Depends(get_current_agent)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MetricReportResponse:
    canonical_payload = json.dumps(
        payload.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    content_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()

    existing = db.scalar(
        select(MetricReport).where(
            MetricReport.agent_id == agent.id,
            MetricReport.report_id == payload.report_id,
        )
    )
    if existing is not None:
        if not secrets.compare_digest(existing.content_hash, content_hash):
            raise APIError(
                409,
                "report_id_conflict",
                "This report ID was already used with different content",
            )
        return MetricReportResponse(
            accepted=True,
            duplicate=True,
            report_id=payload.report_id,
            control=build_agent_control(agent, settings, payload.config_revision),
        )

    db.add(
        MetricReport(
            agent_id=agent.id,
            report_id=payload.report_id,
            schema_version=payload.schema_version,
            content_hash=content_hash,
            observed_at=payload.observed_at,
            payload=payload.model_dump(mode="json"),
        )
    )
    agent.last_seen_at = datetime.now(UTC)
    agent.status = "online"
    db.commit()
    db.refresh(agent)

    return MetricReportResponse(
        accepted=True,
        duplicate=False,
        report_id=payload.report_id,
        control=build_agent_control(agent, settings, payload.config_revision),
    )

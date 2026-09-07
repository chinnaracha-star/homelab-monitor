from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentRegistrationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    hostname: str = Field(min_length=1, max_length=255)
    version: str = Field(min_length=1, max_length=50)
    capabilities: list[str] = Field(default_factory=list, max_length=50)


class AgentRegistrationResponse(BaseModel):
    agent_id: str
    agent_token: str
    report_interval_seconds: int
    config_revision: int
    message: str = "Store this agent token securely; it will not be shown again."


class AgentCheckInRequest(BaseModel):
    version: str = Field(min_length=1, max_length=50)
    observed_at: datetime
    config_revision: int = Field(default=0, ge=0)


class AgentControlResponse(BaseModel):
    next_report_in: int
    config_revision: int
    configuration: dict[str, Any] | None = None
    minimum_agent_version: str
    latest_agent_version: str
    update_available: bool
    commands: list[dict[str, Any]] = Field(default_factory=list)


class ModuleResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    module: str = Field(min_length=1, max_length=50)
    status: Literal["healthy", "warning", "critical", "unknown"]
    summary: str = Field(min_length=1, max_length=500)
    metrics: dict[str, Any] = Field(default_factory=dict)
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class MetricReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str = Field(min_length=1, max_length=64)
    schema_version: str = Field(default="1.0", max_length=20)
    observed_at: datetime
    config_revision: int = Field(default=0, ge=0)
    modules: list[ModuleResult] = Field(min_length=1, max_length=100)


class MetricReportResponse(BaseModel):
    accepted: bool
    duplicate: bool
    report_id: str
    control: AgentControlResponse


class HealthResponse(BaseModel):
    status: Literal["healthy", "degraded"]
    service: str
    version: str
    database: Literal["up", "down"]
    timestamp: datetime


class AgentCountResponse(BaseModel):
    total: int
    online: int
    offline: int


class ReportCountResponse(BaseModel):
    total: int


class DashboardOverviewResponse(BaseModel):
    agents: AgentCountResponse
    reports: ReportCountResponse


class AgentSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    hostname: str
    version: str
    status: str
    last_seen_at: datetime | None


class AgentDetailResponse(AgentSummaryResponse):
    configuration_revision: int
    capabilities: list[str]


class LatestMetricReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    report_id: str
    schema_version: str
    observed_at: datetime
    received_at: datetime
    payload: dict[str, Any]


class ActiveAlertResponse(BaseModel):
    id: str
    agent_id: str
    agent_name: str
    kind: str
    resource: str
    severity: str
    current_value: float | None
    threshold: float | None
    message: str
    opened_at: datetime
    last_observed_at: datetime

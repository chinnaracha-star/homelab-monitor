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


class GroupCountResponse(BaseModel):
    total: int


class GroupOverviewItem(BaseModel):
    id: str
    name: str
    agents: int
    online: int


class DashboardOverviewResponse(BaseModel):
    agents: AgentCountResponse
    reports: ReportCountResponse
    groups: GroupCountResponse
    group_stats: list[GroupOverviewItem]


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


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=72)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class CurrentUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    full_name: str
    role: str
    is_active: bool


class UserResponse(CurrentUserResponse):
    created_at: datetime
    updated_at: datetime


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=72)
    role: Literal["admin", "operator", "viewer"]
    is_active: bool = True


class UserUpdateRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    role: Literal["admin", "operator", "viewer"]
    is_active: bool


class UserPasswordRequest(BaseModel):
    password: str = Field(min_length=8, max_length=72)


class UserStatusRequest(BaseModel):
    is_active: bool


class AlertAcknowledgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    status: str


class GroupCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9 ._-]*$")
    description: str = Field(default="", max_length=500)


class GroupUpdateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9 ._-]*$")
    description: str = Field(default="", max_length=500)


class GroupMembershipRequest(BaseModel):
    agent_ids: list[str] = Field(min_length=1, max_length=200)


class GroupSummaryResponse(BaseModel):
    id: str
    name: str
    description: str
    agents: int
    online: int
    agent_ids: list[str]


class GroupDetailResponse(GroupSummaryResponse):
    created_at: datetime
    updated_at: datetime
    members: list[AgentSummaryResponse]


class GroupSummaryListResponse(BaseModel):
    total: int
    groups: list[GroupSummaryResponse]


class MetricHistoryPoint(BaseModel):
    timestamp: datetime
    cpu_percent: float | None
    memory_percent: float | None
    disk_percent: float | None
    temperature_celsius: float | None
    network_rx_bytes: float | None
    network_tx_bytes: float | None


class MetricHistoryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agent_id: str
    interval: Literal["1m", "5m", "15m", "1h"]
    from_time: datetime = Field(alias="from")
    to_time: datetime = Field(alias="to")
    points: list[MetricHistoryPoint]


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    alert_id: str | None
    channel: str
    recipient: str
    status: str
    error_message: str
    sent_at: datetime | None
    created_at: datetime
    updated_at: datetime


class NotificationListResponse(BaseModel):
    total: int
    notifications: list[NotificationResponse]


class NotificationTestRequest(BaseModel):
    channel: Literal["telegram", "discord", "slack", "email"] | None = None


class TelegramSettingsPublic(BaseModel):
    enabled: bool
    configured: bool
    api_base_url: str
    chat_id: str
    bot_token_set: bool
    last_test: datetime | None = None


class WebhookSettingsPublic(BaseModel):
    enabled: bool
    configured: bool
    webhook_url_set: bool


class EmailSettingsPublic(BaseModel):
    enabled: bool
    configured: bool
    host: str
    port: int
    username: str
    from_address: str
    to_address: str
    use_tls: bool
    password_set: bool


class NotificationSettingsResponse(BaseModel):
    telegram: TelegramSettingsPublic
    discord: WebhookSettingsPublic
    slack: WebhookSettingsPublic
    email: EmailSettingsPublic


class TelegramSettingsUpdate(BaseModel):
    enabled: bool | None = None
    api_base_url: str | None = None
    chat_id: str | None = None
    bot_token: str | None = None


class WebhookSettingsUpdate(BaseModel):
    enabled: bool | None = None
    webhook_url: str | None = None


class EmailSettingsUpdate(BaseModel):
    enabled: bool | None = None
    host: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    username: str | None = None
    password: str | None = None
    from_address: str | None = None
    to_address: str | None = None
    use_tls: bool | None = None


class NotificationSettingsUpdateRequest(BaseModel):
    telegram: TelegramSettingsUpdate | None = None
    discord: WebhookSettingsUpdate | None = None
    slack: WebhookSettingsUpdate | None = None
    email: EmailSettingsUpdate | None = None


class AlertRuleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9 ._-]*$")
    description: str = Field(default="", max_length=500)
    metric: Literal[
        "cpu_percent",
        "memory_percent",
        "disk_percent",
        "temperature_celsius",
        "agent_offline",
    ]
    operator: Literal[">", ">=", "<", "<=", "==", "!="]
    threshold: float
    severity: Literal["critical", "high", "medium", "low"]
    enabled: bool = True
    cooldown_seconds: int = Field(default=0, ge=0, le=86_400)
    applies_to: Literal["all", "group", "agent"] = "all"
    group_id: str | None = None
    agent_id: str | None = None


class AlertRuleUpdateRequest(AlertRuleCreateRequest):
    pass


class AlertRuleEnableRequest(BaseModel):
    enabled: bool


class AlertRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    metric: str
    operator: str
    threshold: float
    severity: str
    enabled: bool
    cooldown_seconds: int
    applies_to: str
    group_id: str | None
    agent_id: str | None
    preview: str
    created_at: datetime
    updated_at: datetime


class InfrastructureSnapshotResponse(BaseModel):
    service: str
    status: str
    version: str
    updated_at: datetime
    summary: dict[str, Any]


class InfrastructureSummaryResponse(BaseModel):
    collected_at: datetime
    services: list[InfrastructureSnapshotResponse]


class StorageHistoryResponse(BaseModel):
    today: int = 0
    yesterday: int = 0
    last_week: int = 0


class PhotoGrowthResponse(BaseModel):
    today: int = 0
    yesterday: int = 0
    this_week: int = 0


class PhotoStatsResponse(BaseModel):
    indexed_photos: int = 0
    indexed_videos: int = 0
    albums: int = 0
    users: int = 0
    storage_used: int = 0
    storage_free: int = 0
    storage_percent: float = 0
    thumbnail_queue: int = 0
    face_queue: int = 0
    last_scan: str = ""
    capacity_bytes: int = 0
    storage_health: str = "unknown"
    storage_percent_metric: float = 0
    thumbnail_queue_metric: int = 0
    face_queue_metric: int = 0
    immich_health: int = 0
    qumagie_health: int = 0
    storage_history: StorageHistoryResponse = StorageHistoryResponse()
    photo_growth: PhotoGrowthResponse = PhotoGrowthResponse()


class PhotoServicesResponse(BaseModel):
    collected_at: datetime
    read_only: bool = True
    services: list[InfrastructureSnapshotResponse]
    stats: PhotoStatsResponse


class BackupDestinationResponse(BaseModel):
    hostname: str = ""
    ip: str = ""
    model: str = "TS-253 Pro"


class BackupHistoryPeriodResponse(BaseModel):
    period: str
    label: str
    status: str


class BackupStatusResponse(BaseModel):
    read_only: bool = True
    status: str
    backup_health: str = "unknown"
    job_name: str = ""
    job_type: str = ""
    progress_percent: float = 0
    last_backup: str = ""
    next_backup: str = ""
    duration_seconds: int = 0
    backup_size_bytes: int = 0
    last_error: str = ""
    last_success: str = ""
    updated_at: datetime
    destination: BackupDestinationResponse
    history: list[BackupHistoryPeriodResponse] = []

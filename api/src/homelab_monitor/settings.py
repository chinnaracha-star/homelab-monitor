from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="HOMELAB_",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    environment: str = "development"
    database_url: str = "sqlite:///./data/homelab-monitor.db"
    log_level: str = "INFO"
    registration_key: str = Field(min_length=24)
    agent_report_interval_seconds: int = Field(default=60, ge=15, le=3600)
    minimum_agent_version: str = "0.1.0"
    latest_agent_version: str = "0.1.0"
    alert_cpu_threshold_percent: float = Field(default=90.0, ge=0, le=100)
    alert_memory_threshold_percent: float = Field(default=90.0, ge=0, le=100)
    alert_disk_threshold_percent: float = Field(default=90.0, ge=0, le=100)
    alert_temperature_threshold_celsius: float = Field(default=85.0, ge=-100, le=250)
    agent_offline_after_seconds: int = Field(default=180, ge=30, le=86_400)
    alert_evaluation_interval_seconds: int = Field(default=30, ge=5, le=3600)
    telegram_api_base_url: str = Field(
        default="",
        validation_alias=AliasChoices(
            "TELEGRAM_API_BASE_URL",
            "HOMELAB_TELEGRAM_API_BASE_URL",
        ),
    )
    telegram_bot_token: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "TELEGRAM_BOT_TOKEN",
            "HOMELAB_TELEGRAM_BOT_TOKEN",
        ),
    )
    telegram_chat_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "TELEGRAM_CHAT_ID",
            "HOMELAB_TELEGRAM_CHAT_ID",
        ),
    )
    telegram_request_timeout: float = Field(
        default=10.0,
        gt=0,
        le=120,
        validation_alias=AliasChoices(
            "TELEGRAM_REQUEST_TIMEOUT",
            "HOMELAB_TELEGRAM_REQUEST_TIMEOUT",
        ),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

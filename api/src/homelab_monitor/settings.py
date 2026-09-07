from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="HOMELAB_",
        case_sensitive=False,
        extra="ignore",
    )

    environment: str = "development"
    database_url: str = "sqlite:///./data/homelab-monitor.db"
    log_level: str = "INFO"
    registration_key: str = Field(min_length=24)
    agent_report_interval_seconds: int = Field(default=60, ge=15, le=3600)
    minimum_agent_version: str = "0.1.0"
    latest_agent_version: str = "0.1.0"
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

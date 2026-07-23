"""Worker-side settings (mirrors backend config but only the bits we need)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    mongodb_url: str = "mongodb://mongodb:27017"
    mongodb_database: str = "iwasist"

    temporal_address: str = "temporal:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "meeting-processing-queue"

    whisper_service_url: str = "http://whisper:9000"

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "openrouter/free"


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()

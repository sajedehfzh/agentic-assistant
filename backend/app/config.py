"""Application settings loaded from environment variables.

Centralizing all config here keeps the rest of the codebase oblivious to
where values come from. To change runtime behavior, edit `.env` (or set env
vars in `docker-compose.yml`) — not Python code.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "production", "test"] = "development"
    frontend_url: str = "http://localhost:3000"
    uploads_dir: str = "/uploads"

    mongodb_url: str = "mongodb://mongodb:27017"
    mongodb_database: str = "iwasist"

    temporal_address: str = "temporal:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "meeting-processing-queue"

    whisper_service_url: str = "http://whisper:9000"
    max_audio_upload_mb: int = 200

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "openrouter/free"

    auth_provider: Literal["simple", "oauth"] = "simple"
    auth_username: str = "admin"
    auth_password: str = "admin"
    jwt_secret_key: str = "change-me-in-production-please"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    oauth_google_client_id: str = ""
    oauth_google_client_secret: str = ""
    oauth_github_client_id: str = ""
    oauth_github_client_secret: str = ""

    cors_allow_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
        ]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

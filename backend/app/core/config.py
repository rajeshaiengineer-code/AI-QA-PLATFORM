"""
Application Configuration Module

Uses Pydantic Settings for environment management with validation.
Supports .env files and environment variables.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "AI QA Platform"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Enterprise-grade AI-powered Quality Assurance Platform"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # API
    API_V1_PREFIX: str = "/api/v1"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_qa_platform"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_ECHO: bool = False

    # Security / Auth
    SECRET_KEY: str = "your-super-secret-key-change-in-production-min-32-chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"
    # When False (default), JWT is not required — existing tests keep working.
    # When True, protected routes require a valid Bearer access token.
    AUTH_ENABLED: bool = False

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # "json" or "text"

    # AI Framework
    AI_DEFAULT_PROVIDER: str = "openai"
    AI_DEFAULT_MODEL: str = "gpt-4o-mini"
    AI_REQUEST_TIMEOUT_SECONDS: float = 60.0

    AI_OPENAI_API_KEY: Optional[str] = None
    AI_OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    AI_OPENAI_DEFAULT_MODEL: str = "gpt-4o-mini"

    AI_GEMINI_API_KEY: Optional[str] = None
    AI_GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    AI_GEMINI_DEFAULT_MODEL: str = "gemini-flash-latest"

    AI_CLAUDE_API_KEY: Optional[str] = None
    AI_CLAUDE_BASE_URL: str = "https://api.anthropic.com/v1"
    AI_CLAUDE_DEFAULT_MODEL: str = "claude-sonnet-4-20250514"
    AI_CLAUDE_API_VERSION: str = "2023-06-01"

    # Amazon Bedrock (API key / bearer token — see docs/AIFramework.md)
    AI_BEDROCK_API_KEY: Optional[str] = None
    AI_BEDROCK_REGION: str = "us-east-1"
    AI_BEDROCK_BASE_URL: Optional[str] = None
    AI_BEDROCK_DEFAULT_MODEL: str = "amazon.nova-lite-v1:0"

    # Notifications
    # Email uses an SMTP stub that logs instead of opening a real connection
    # unless SMTP_HOST is set (still stubbed in MVP — no real SMTP send).
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: str = "noreply@ai-qa-platform.local"
    SMTP_USE_TLS: bool = True
    SLACK_WEBHOOK_URL: Optional[str] = None
    TEAMS_WEBHOOK_URL: Optional[str] = None
    # Persist NotificationLog rows on send (disable for fire-and-forget only).
    NOTIFICATIONS_PERSIST: bool = True
    # Subscribe to WORKFLOW_COMPLETED / WORKFLOW_FAILED on the EventBus.
    NOTIFICATIONS_WORKFLOW_HOOK: bool = True
    # Default recipient for workflow lifecycle notifications (email / channel id).
    NOTIFICATIONS_DEFAULT_RECIPIENT: Optional[str] = None
    NOTIFICATIONS_DEFAULT_CHANNEL: str = "email"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            # Handle JSON array format
            if v.startswith("["):
                import json
                return json.loads(v)
            # Handle comma-separated format
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("CORS_ALLOW_METHODS", "CORS_ALLOW_HEADERS", mode="before")
    @classmethod
    def parse_cors_lists(cls, v):
        if isinstance(v, str):
            if v.startswith("["):
                import json
                return json.loads(v)
            return [item.strip() for item in v.split(",")]
        return v

    @property
    def database_url_sync(self) -> str:
        """Return sync database URL for Alembic (using psycopg3)."""
        return self.DATABASE_URL.replace("+asyncpg", "+psycopg")

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

"""
AI configuration helpers — env-backed settings for the AI framework.
"""

from typing import Dict, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class AISettings(BaseSettings):
    """
    AI-specific settings loaded from environment / `.env`.

    These mirror fields on `app.core.config.Settings` so either path works.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

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

    AI_BEDROCK_API_KEY: Optional[str] = None
    AI_BEDROCK_REGION: str = "us-east-1"
    AI_BEDROCK_BASE_URL: Optional[str] = None
    AI_BEDROCK_DEFAULT_MODEL: str = "amazon.nova-lite-v1:0"


class AIConfig:
    """
    Convenience facade over AISettings for providers and runtime wiring.
    """

    def __init__(self, settings: Optional[AISettings] = None) -> None:
        self.settings = settings or AISettings()

    @property
    def default_provider(self) -> str:
        return self.settings.AI_DEFAULT_PROVIDER.strip().lower()

    @property
    def default_model(self) -> str:
        return self.settings.AI_DEFAULT_MODEL

    @property
    def timeout(self) -> float:
        return float(self.settings.AI_REQUEST_TIMEOUT_SECONDS)

    def api_key_for(self, provider: str) -> Optional[str]:
        key = provider.strip().lower()
        mapping = {
            "openai": self.settings.AI_OPENAI_API_KEY,
            "gemini": self.settings.AI_GEMINI_API_KEY,
            "claude": self.settings.AI_CLAUDE_API_KEY,
            "bedrock": self.settings.AI_BEDROCK_API_KEY,
        }
        return mapping.get(key)

    def base_url_for(self, provider: str) -> Optional[str]:
        key = provider.strip().lower()
        if key == "bedrock":
            if self.settings.AI_BEDROCK_BASE_URL:
                return self.settings.AI_BEDROCK_BASE_URL
            region = self.settings.AI_BEDROCK_REGION or "us-east-1"
            return f"https://bedrock-runtime.{region}.amazonaws.com"
        mapping = {
            "openai": self.settings.AI_OPENAI_BASE_URL,
            "gemini": self.settings.AI_GEMINI_BASE_URL,
            "claude": self.settings.AI_CLAUDE_BASE_URL,
        }
        return mapping.get(key)

    def default_model_for(self, provider: str) -> Optional[str]:
        key = provider.strip().lower()
        mapping = {
            "openai": self.settings.AI_OPENAI_DEFAULT_MODEL,
            "gemini": self.settings.AI_GEMINI_DEFAULT_MODEL,
            "claude": self.settings.AI_CLAUDE_DEFAULT_MODEL,
            "bedrock": self.settings.AI_BEDROCK_DEFAULT_MODEL,
        }
        return mapping.get(key)

    def credential_env_map(self) -> Dict[str, Optional[str]]:
        """Provider name → API key from env (may be None)."""
        return {
            "openai": self.settings.AI_OPENAI_API_KEY,
            "gemini": self.settings.AI_GEMINI_API_KEY,
            "claude": self.settings.AI_CLAUDE_API_KEY,
            "bedrock": self.settings.AI_BEDROCK_API_KEY,
        }


def get_ai_config() -> AIConfig:
    """Build AIConfig, preferring values from app.core.config when available."""
    try:
        from app.core.config import settings as app_settings

        ai_settings = AISettings(
            AI_DEFAULT_PROVIDER=getattr(
                app_settings, "AI_DEFAULT_PROVIDER", "openai"
            ),
            AI_DEFAULT_MODEL=getattr(app_settings, "AI_DEFAULT_MODEL", "gpt-4o-mini"),
            AI_REQUEST_TIMEOUT_SECONDS=getattr(
                app_settings, "AI_REQUEST_TIMEOUT_SECONDS", 60.0
            ),
            AI_OPENAI_API_KEY=getattr(app_settings, "AI_OPENAI_API_KEY", None),
            AI_OPENAI_BASE_URL=getattr(
                app_settings, "AI_OPENAI_BASE_URL", "https://api.openai.com/v1"
            ),
            AI_OPENAI_DEFAULT_MODEL=getattr(
                app_settings, "AI_OPENAI_DEFAULT_MODEL", "gpt-4o-mini"
            ),
            AI_GEMINI_API_KEY=getattr(app_settings, "AI_GEMINI_API_KEY", None),
            AI_GEMINI_BASE_URL=getattr(
                app_settings,
                "AI_GEMINI_BASE_URL",
                "https://generativelanguage.googleapis.com/v1beta",
            ),
            AI_GEMINI_DEFAULT_MODEL=getattr(
                app_settings, "AI_GEMINI_DEFAULT_MODEL", "gemini-flash-latest"
            ),
            AI_CLAUDE_API_KEY=getattr(app_settings, "AI_CLAUDE_API_KEY", None),
            AI_CLAUDE_BASE_URL=getattr(
                app_settings, "AI_CLAUDE_BASE_URL", "https://api.anthropic.com/v1"
            ),
            AI_CLAUDE_DEFAULT_MODEL=getattr(
                app_settings, "AI_CLAUDE_DEFAULT_MODEL", "claude-sonnet-4-20250514"
            ),
            AI_CLAUDE_API_VERSION=getattr(
                app_settings, "AI_CLAUDE_API_VERSION", "2023-06-01"
            ),
            AI_BEDROCK_API_KEY=getattr(app_settings, "AI_BEDROCK_API_KEY", None),
            AI_BEDROCK_REGION=getattr(app_settings, "AI_BEDROCK_REGION", "us-east-1"),
            AI_BEDROCK_BASE_URL=getattr(app_settings, "AI_BEDROCK_BASE_URL", None),
            AI_BEDROCK_DEFAULT_MODEL=getattr(
                app_settings, "AI_BEDROCK_DEFAULT_MODEL", "amazon.nova-lite-v1:0"
            ),
        )
        return AIConfig(ai_settings)
    except Exception:
        return AIConfig()

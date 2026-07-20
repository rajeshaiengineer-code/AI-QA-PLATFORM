"""
Unit tests for startup environment validation.
"""

import pytest

from app.core.config import Settings
from app.core.validation import validate_settings


def _settings(**overrides) -> Settings:
    """Build Settings without reading .env (isolated unit tests)."""
    base = {
        "ENVIRONMENT": "development",
        "DEBUG": True,
        "SECRET_KEY": "dev-only-not-for-production-use-xxxxxx",
        "DATABASE_URL": "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_qa_platform",
        "LOG_FORMAT": "text",
        "DATABASE_POOL_SIZE": 5,
        "DATABASE_MAX_OVERFLOW": 10,
        "DATABASE_POOL_TIMEOUT": 30,
    }
    base.update(overrides)
    return Settings(**base)


class TestValidateSettings:
    def test_development_defaults_ok(self):
        validate_settings(_settings())

    def test_invalid_log_format(self):
        with pytest.raises(RuntimeError, match="LOG_FORMAT"):
            validate_settings(_settings(LOG_FORMAT="xml"))

    def test_production_rejects_placeholder_secret(self):
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            validate_settings(
                _settings(
                    ENVIRONMENT="production",
                    DEBUG=False,
                    LOG_FORMAT="json",
                    SECRET_KEY="your-super-secret-key-change-in-production-min-32-chars",
                )
            )

    def test_production_rejects_debug(self):
        with pytest.raises(RuntimeError, match="DEBUG"):
            validate_settings(
                _settings(
                    ENVIRONMENT="production",
                    DEBUG=True,
                    LOG_FORMAT="json",
                    SECRET_KEY="a" * 32,
                )
            )

    def test_production_ok(self):
        validate_settings(
            _settings(
                ENVIRONMENT="production",
                DEBUG=False,
                LOG_FORMAT="json",
                SECRET_KEY="a" * 32,
                AUTH_ENABLED=True,
            )
        )

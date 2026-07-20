"""
Startup environment validation.

Fails fast when production (or misconfigured) settings are unsafe.
Required variables are documented in docs/ProductionReadiness.md and .env.example files.
"""

from __future__ import annotations

from typing import List

from app.core.config import Settings

# Placeholder secrets that must never be used when ENVIRONMENT=production
_INSECURE_SECRET_KEYS = frozenset(
    {
        "your-super-secret-key-change-in-production",
        "your-super-secret-key-change-in-production-min-32-chars",
        "change-me",
        "secret",
    }
)

_VALID_LOG_FORMATS = frozenset({"json", "text"})
_VALID_ENVIRONMENTS = frozenset(
    {"development", "test", "staging", "production"}
)


def validate_settings(settings: Settings) -> None:
    """
    Validate application settings.

    Raises:
        RuntimeError: when configuration is invalid for the current environment.
    """
    errors: List[str] = []

    env = (settings.ENVIRONMENT or "").strip().lower()
    if env and env not in _VALID_ENVIRONMENTS:
        errors.append(
            f"ENVIRONMENT must be one of {sorted(_VALID_ENVIRONMENTS)}, got {settings.ENVIRONMENT!r}"
        )

    log_format = (settings.LOG_FORMAT or "").strip().lower()
    if log_format not in _VALID_LOG_FORMATS:
        errors.append(
            f"LOG_FORMAT must be 'json' or 'text', got {settings.LOG_FORMAT!r}"
        )

    if not settings.DATABASE_URL or not settings.DATABASE_URL.strip():
        errors.append("DATABASE_URL is required")

    if settings.DATABASE_POOL_SIZE < 1:
        errors.append("DATABASE_POOL_SIZE must be >= 1")
    if settings.DATABASE_MAX_OVERFLOW < 0:
        errors.append("DATABASE_MAX_OVERFLOW must be >= 0")
    if settings.DATABASE_POOL_TIMEOUT < 1:
        errors.append("DATABASE_POOL_TIMEOUT must be >= 1")

    if settings.is_production:
        secret = (settings.SECRET_KEY or "").strip()
        if not secret or secret in _INSECURE_SECRET_KEYS or len(secret) < 32:
            errors.append(
                "SECRET_KEY must be a strong random value (≥32 characters) in production; "
                "do not use the example placeholder"
            )
        if settings.DEBUG:
            errors.append("DEBUG must be false when ENVIRONMENT=production")
        if log_format != "json":
            errors.append(
                "LOG_FORMAT must be 'json' in production for structured log aggregation"
            )

    if errors:
        joined = "; ".join(errors)
        raise RuntimeError(f"Invalid configuration: {joined}")

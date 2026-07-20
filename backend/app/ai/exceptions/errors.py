"""
AI Framework Exceptions
"""

from typing import Any, Dict, Optional


class AIError(Exception):
    """Base error for the AI framework."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "AI_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class AIProviderNotFoundError(AIError):
    """Requested AI provider is not registered."""

    def __init__(self, name: str) -> None:
        super().__init__(
            f"AI provider '{name}' is not registered",
            code="AI_PROVIDER_NOT_FOUND",
            details={"name": name},
        )


class AIProviderDisabledError(AIError):
    """Provider exists but is disabled."""

    def __init__(self, name: str) -> None:
        super().__init__(
            f"AI provider '{name}' is disabled",
            code="AI_PROVIDER_DISABLED",
            details={"name": name},
        )


class AIProviderAlreadyRegisteredError(AIError):
    """Duplicate registration attempt."""

    def __init__(self, name: str) -> None:
        super().__init__(
            f"AI provider '{name}' is already registered",
            code="AI_PROVIDER_ALREADY_REGISTERED",
            details={"name": name},
        )


class AIConfigurationError(AIError):
    """Invalid or incomplete AI configuration."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message,
            code="AI_CONFIGURATION_ERROR",
            details=details,
        )


class AICredentialError(AIError):
    """Missing, invalid, or unsupported AI credentials."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message,
            code="AI_CREDENTIAL_ERROR",
            details=details,
        )


class AIGenerationError(AIError):
    """Provider failed to generate a completion."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message,
            code="AI_GENERATION_ERROR",
            details=details,
        )


class AIModelNotFoundError(AIError):
    """Logical model name is not registered."""

    def __init__(self, name: str) -> None:
        super().__init__(
            f"Logical model '{name}' is not registered",
            code="AI_MODEL_NOT_FOUND",
            details={"name": name},
        )


class PromptNotFoundError(AIError):
    """Prompt template is missing."""

    def __init__(self, name: str) -> None:
        super().__init__(
            f"Prompt template '{name}' was not found",
            code="PROMPT_NOT_FOUND",
            details={"name": name},
        )


class PromptRenderError(AIError):
    """Prompt template could not be rendered."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message,
            code="PROMPT_RENDER_ERROR",
            details=details,
        )

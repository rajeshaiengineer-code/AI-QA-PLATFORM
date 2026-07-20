"""AI provider base contract and shared types."""

from app.ai.base.provider import BaseAIProvider
from app.ai.base.types import (
    AIHealth,
    AIProviderMetadata,
    AIProviderName,
    ChatMessage,
    GenerateRequest,
    GenerateResponse,
    HealthStatus,
    MessageRole,
    ModelBinding,
    TokenUsage,
)

__all__ = [
    "BaseAIProvider",
    "AIHealth",
    "AIProviderMetadata",
    "AIProviderName",
    "ChatMessage",
    "GenerateRequest",
    "GenerateResponse",
    "HealthStatus",
    "MessageRole",
    "ModelBinding",
    "TokenUsage",
]

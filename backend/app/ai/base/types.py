"""
Shared AI framework types and value objects.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AIProviderName(str, Enum):
    """Built-in AI provider keys."""

    OPENAI = "openai"
    GEMINI = "gemini"
    CLAUDE = "claude"


class HealthStatus(str, Enum):
    """AI provider health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class MessageRole(str, Enum):
    """Chat message role."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    """Single chat turn."""

    role: MessageRole
    content: str


class GenerateRequest(BaseModel):
    """Provider-agnostic generation request."""

    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.2
    max_tokens: Optional[int] = 1024
    top_p: Optional[float] = None
    stop: Optional[List[str]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TokenUsage(BaseModel):
    """Token accounting when the provider reports it."""

    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None


class GenerateResponse(BaseModel):
    """Normalized generation response."""

    content: str
    model: str
    provider: str
    finish_reason: Optional[str] = None
    usage: Optional[TokenUsage] = None
    raw: Dict[str, Any] = Field(default_factory=dict)


class AIProviderMetadata(BaseModel):
    """Static descriptor for an AI provider plugin."""

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Unique provider key, e.g. 'openai'")
    display_name: str
    version: str = "0.1.0"
    description: str = ""
    homepage: Optional[str] = None
    default_model: str = ""
    supported_models: List[str] = Field(default_factory=list)
    capabilities: List[str] = Field(default_factory=list)


class AIHealth(BaseModel):
    """Result of an AI provider health_check()."""

    status: HealthStatus = HealthStatus.UNKNOWN
    provider: str
    latency_ms: Optional[float] = None
    last_checked: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class ModelBinding(BaseModel):
    """
    Maps a logical model name (used by application code) to a concrete
    provider + remote model id.
    """

    model_config = ConfigDict(frozen=True)

    logical_name: str
    provider: str
    model: str
    description: str = ""
    enabled: bool = True

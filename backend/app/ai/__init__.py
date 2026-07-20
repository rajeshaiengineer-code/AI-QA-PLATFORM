"""
AI Framework

Provider-agnostic LLM abstraction for the AI QA Platform.
Business agents (e.g. Story Analyzer) build on top of this package.
"""

from app.ai.base import (
    AIHealth,
    AIProviderMetadata,
    AIProviderName,
    BaseAIProvider,
    ChatMessage,
    GenerateRequest,
    GenerateResponse,
    HealthStatus,
    MessageRole,
    ModelBinding,
    TokenUsage,
)
from app.ai.config import AIConfig, AISettings, get_ai_config
from app.ai.exceptions import (
    AIConfigurationError,
    AICredentialError,
    AIError,
    AIGenerationError,
    AIModelNotFoundError,
    AIProviderAlreadyRegisteredError,
    AIProviderDisabledError,
    AIProviderNotFoundError,
    PromptNotFoundError,
    PromptRenderError,
)
from app.ai.factory import AIProviderFactory
from app.ai.models import ModelRegistry
from app.ai.prompts import PromptManager
from app.ai.providers import (
    BedrockProvider,
    ClaudeProvider,
    GeminiProvider,
    OpenAIProvider,
)
from app.ai.registry import (
    AIProviderRegistration,
    AIProviderRegistry,
    default_ai_registry,
)

__all__ = [
    "AIHealth",
    "AIProviderMetadata",
    "AIProviderName",
    "BaseAIProvider",
    "ChatMessage",
    "GenerateRequest",
    "GenerateResponse",
    "HealthStatus",
    "MessageRole",
    "ModelBinding",
    "TokenUsage",
    "AIConfig",
    "AISettings",
    "get_ai_config",
    "AIError",
    "AIProviderNotFoundError",
    "AIProviderDisabledError",
    "AIProviderAlreadyRegisteredError",
    "AIConfigurationError",
    "AICredentialError",
    "AIGenerationError",
    "AIModelNotFoundError",
    "PromptNotFoundError",
    "PromptRenderError",
    "AIProviderFactory",
    "ModelRegistry",
    "PromptManager",
    "OpenAIProvider",
    "GeminiProvider",
    "ClaudeProvider",
    "BedrockProvider",
    "AIProviderRegistration",
    "AIProviderRegistry",
    "default_ai_registry",
]

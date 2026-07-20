"""
Shared AI runtime — process-wide registry, factory, prompts, and models.

Providers register here at app startup. Application code resolves providers
via the factory and logical models via ModelRegistry.
"""

from typing import Optional

from app.ai.config import AIConfig, get_ai_config
from app.ai.factory import AIProviderFactory
from app.ai.models import ModelRegistry
from app.ai.base.types import ModelBinding
from app.ai.prompts import PromptManager
from app.ai.registry import AIProviderRegistry
from app.connectors.base.types import CredentialType
from app.connectors.credentials import CredentialManager
from app.connectors.credentials.models import ConnectorCredentials
from app.connectors.runtime import credential_manager as shared_credential_manager

ai_provider_registry = AIProviderRegistry()
model_registry = ModelRegistry()
prompt_manager = PromptManager()
ai_config: AIConfig = get_ai_config()

ai_factory = AIProviderFactory(
    registry=ai_provider_registry,
    credential_manager=shared_credential_manager,
)


def register_builtin_ai_providers(
    *,
    credential_manager: Optional[CredentialManager] = None,
    config: Optional[AIConfig] = None,
) -> None:
    """
    Register shipped AI provider plugins and seed defaults (idempotent).

    Also loads API keys from AI_* env vars into the Credential Manager when
    present, so factories can resolve credentials by provider name.
    """
    from app.ai.providers.bedrock import BedrockProvider
    from app.ai.providers.claude import ClaudeProvider
    from app.ai.providers.gemini import GeminiProvider
    from app.ai.providers.openai import OpenAIProvider

    global ai_config
    cfg = config or get_ai_config()
    ai_config = cfg

    creds = credential_manager or shared_credential_manager

    if not ai_provider_registry.is_registered("openai"):
        ai_provider_registry.register(OpenAIProvider)
    if not ai_provider_registry.is_registered("gemini"):
        ai_provider_registry.register(GeminiProvider)
    if not ai_provider_registry.is_registered("claude"):
        ai_provider_registry.register(ClaudeProvider)
    if not ai_provider_registry.is_registered("bedrock"):
        ai_provider_registry.register(BedrockProvider)

    _seed_credentials_from_env(creds, cfg)
    _seed_default_models(cfg)

    # Keep factory credential manager in sync if a custom one is passed
    if credential_manager is not None:
        ai_factory.credential_manager = credential_manager


def _seed_credentials_from_env(
    creds: CredentialManager,
    cfg: AIConfig,
) -> None:
    for provider_name, api_key in cfg.credential_env_map().items():
        if not api_key:
            continue
        # Always refresh from env so rotated keys take effect on restart.
        creds.save(
            ConnectorCredentials(
                connector_name=provider_name,
                credential_type=CredentialType.API_KEY,
                api_key=api_key,
            )
        )


def _seed_default_models(cfg: AIConfig) -> None:
    """Register logical model aliases used by upcoming agents."""
    default_provider = cfg.default_provider
    default_model = (
        cfg.default_model_for(default_provider) or cfg.default_model
    )
    defaults = [
        ModelBinding(
            logical_name="default",
            provider=default_provider,
            model=default_model,
            description="Platform default model",
        ),
        ModelBinding(
            logical_name="fast",
            provider=default_provider,
            model=default_model,
            description="Low-latency model (same as platform default)",
        ),
        ModelBinding(
            logical_name="balanced",
            provider="claude",
            model=cfg.settings.AI_CLAUDE_DEFAULT_MODEL,
            description="Balanced Claude model",
        ),
        ModelBinding(
            logical_name="gemini-flash",
            provider="gemini",
            model=cfg.settings.AI_GEMINI_DEFAULT_MODEL,
            description="Gemini flash model",
        ),
        ModelBinding(
            logical_name="bedrock-nova",
            provider="bedrock",
            model=cfg.settings.AI_BEDROCK_DEFAULT_MODEL,
            description="Amazon Bedrock Nova",
        ),
    ]
    for binding in defaults:
        existing = model_registry.get_or_none(binding.logical_name)
        if existing is None:
            model_registry.register(binding)
        elif binding.logical_name == "default":
            # Keep "default" aligned with current env on every startup.
            model_registry.register(binding, overwrite=True)

"""
AI Provider Factory — instantiate providers with dependency injection.
"""

from typing import Any, Dict, Optional, Type

from app.ai.base.provider import BaseAIProvider
from app.ai.exceptions import AIConfigurationError
from app.ai.registry.registry import AIProviderRegistry, default_ai_registry
from app.connectors.credentials.manager import CredentialManager
from app.connectors.credentials.models import ConnectorCredentials


class AIProviderFactory:
    """
    Creates AI provider instances from the registry.

    Optionally resolves API keys from CredentialManager using the provider
    name as the credential key (aligned with the Connector Framework).
    """

    def __init__(
        self,
        registry: Optional[AIProviderRegistry] = None,
        credential_manager: Optional[CredentialManager] = None,
        default_dependencies: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.registry = registry or default_ai_registry
        self.credential_manager = credential_manager
        self.default_dependencies = default_dependencies or {}

    def create(
        self,
        name: str,
        *,
        credentials: Optional[ConnectorCredentials] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        load_credentials: bool = True,
        require_enabled: bool = True,
        timeout: Optional[float] = None,
        **dependencies: Any,
    ) -> BaseAIProvider:
        """
        Instantiate an AI provider by registered name.

        Args:
            name: Registered provider key (openai / gemini / claude).
            credentials: Optional credentials override.
            api_key: Optional explicit API key override.
            base_url: Optional provider base URL override.
            load_credentials: If True, load from CredentialManager when
                credentials / api_key are not provided.
            require_enabled: Fail if the provider is disabled.
            timeout: Optional HTTP timeout override.
            **dependencies: Extra kwargs injected into the provider constructor.
        """
        provider_cls: Type[BaseAIProvider] = self.registry.get_class(
            name,
            require_enabled=require_enabled,
        )

        resolved_credentials = credentials
        if (
            resolved_credentials is None
            and api_key is None
            and load_credentials
            and self.credential_manager is not None
        ):
            resolved_credentials = self.credential_manager.get(name.strip().lower())

        merged = {**self.default_dependencies, **dependencies}
        resolved_base_url = base_url
        resolved_region = merged.pop("region", None)
        if resolved_base_url is None or resolved_region is None:
            try:
                from app.ai.config import get_ai_config

                cfg = get_ai_config()
                if resolved_base_url is None:
                    resolved_base_url = cfg.base_url_for(name)
                if resolved_region is None and name.strip().lower() == "bedrock":
                    resolved_region = cfg.settings.AI_BEDROCK_REGION
            except Exception:
                pass

        kwargs: Dict[str, Any] = {
            "credentials": resolved_credentials,
            "api_key": api_key,
            "base_url": resolved_base_url,
            **merged,
        }
        if resolved_region is not None:
            kwargs["region"] = resolved_region
        if timeout is not None:
            kwargs["timeout"] = timeout

        return provider_cls(**kwargs)

    def create_from_class(
        self,
        provider_cls: Type[BaseAIProvider],
        *,
        credentials: Optional[ConnectorCredentials] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **dependencies: Any,
    ) -> BaseAIProvider:
        """Instantiate without registry lookup (useful in tests)."""
        if not issubclass(provider_cls, BaseAIProvider):
            raise AIConfigurationError(
                "provider_cls must subclass BaseAIProvider",
                details={"provider_cls": getattr(provider_cls, "__name__", str(provider_cls))},
            )
        merged = {**self.default_dependencies, **dependencies}
        return provider_cls(
            credentials=credentials,
            api_key=api_key,
            base_url=base_url,
            **merged,
        )

"""
BaseAIProvider — abstract contract every AI provider plugin must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.ai.base.types import (
    AIHealth,
    AIProviderMetadata,
    GenerateRequest,
    GenerateResponse,
)
from app.connectors.credentials.models import ConnectorCredentials


class BaseAIProvider(ABC):
    """
    Abstract AI provider plugin.

    Lifecycle (typical):
      1. Factory instantiates with credentials (+ optional config)
      2. generate() / health_check()
    """

    def __init__(
        self,
        credentials: Optional[ConnectorCredentials] = None,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 60.0,
        **dependencies: Any,
    ) -> None:
        self.credentials = credentials
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.dependencies = dependencies

    @abstractmethod
    def metadata(self) -> AIProviderMetadata:
        """Return static plugin metadata."""

    @abstractmethod
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Generate a completion for the given request."""

    @abstractmethod
    async def health_check(self) -> AIHealth:
        """Probe credentials / connectivity without a heavyweight prompt."""

    def resolve_api_key(self) -> Optional[str]:
        """Resolve API key from explicit arg or Credential Manager payload."""
        if self.api_key:
            return self.api_key
        if self.credentials is None:
            return None
        key = self.credentials.get_secret_value("api_key")
        if key:
            return key
        return self.credentials.get_secret_value("access_token")

    def require_api_key(self) -> str:
        """Return API key or raise a clear credential error."""
        from app.ai.exceptions import AICredentialError

        key = self.resolve_api_key()
        if not key:
            meta = self.metadata()
            raise AICredentialError(
                f"API key missing for AI provider '{meta.name}'. "
                f"Set the AI_{meta.name.upper()}_API_KEY environment variable "
                f"or store credentials via CredentialManager "
                f"(connector_name='{meta.name}').",
                details={"provider": meta.name},
            )
        return key

    def as_dict(self) -> Dict[str, Any]:
        """Safe summary for diagnostics (no secrets)."""
        meta = self.metadata()
        return {
            "name": meta.name,
            "display_name": meta.display_name,
            "version": meta.version,
            "default_model": meta.default_model,
            "has_api_key": bool(self.resolve_api_key()),
        }

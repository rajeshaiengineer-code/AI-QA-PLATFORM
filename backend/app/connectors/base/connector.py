"""
BaseConnector — abstract contract every provider plugin must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.connectors.base.types import (
    ConfigurationSchema,
    ConnectorHealth,
    ConnectorMetadata,
)
from app.connectors.config.models import ConnectorConfig
from app.connectors.credentials.models import ConnectorCredentials


class BaseConnector(ABC):
    """
    Abstract connector plugin.

    Lifecycle (typical):
      1. Factory instantiates with config + credentials
      2. validate_credentials()
      3. connect()
      4. health_check() / domain operations (provider-specific)
      5. disconnect()
    """

    def __init__(
        self,
        config: Optional[ConnectorConfig] = None,
        credentials: Optional[ConnectorCredentials] = None,
        **dependencies: Any,
    ) -> None:
        self.config = config
        self.credentials = credentials
        self.dependencies = dependencies
        self._connected: bool = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    @abstractmethod
    def metadata(self) -> ConnectorMetadata:
        """Return static plugin metadata."""

    @abstractmethod
    def configuration_schema(self) -> ConfigurationSchema:
        """Return the versioned configuration schema for this connector."""

    @abstractmethod
    async def validate_credentials(self) -> bool:
        """
        Validate that credentials are present and structurally usable.

        Does not necessarily call the remote API (providers may choose to).
        """

    @abstractmethod
    async def connect(self) -> None:
        """Establish a session / client with the remote system."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Release remote resources and mark the connector disconnected."""

    @abstractmethod
    async def health_check(self) -> ConnectorHealth:
        """
        Probe connectivity and return status, version, latency, last_checked.
        """

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Read a value from the connector settings map."""
        if self.config is None:
            return default
        return self.config.settings.get(key, default)

    def as_dict(self) -> Dict[str, Any]:
        """Safe summary for diagnostics (no secrets)."""
        meta = self.metadata()
        return {
            "name": meta.name,
            "display_name": meta.display_name,
            "version": meta.version,
            "category": meta.category.value,
            "connected": self._connected,
            "environment": self.config.environment.value if self.config else None,
        }

"""
Connector Factory — instantiate connectors with dependency injection.
"""

from typing import Any, Dict, Optional, Type

from app.connectors.base.connector import BaseConnector
from app.connectors.config.models import ConnectorConfig
from app.connectors.credentials.manager import CredentialManager
from app.connectors.credentials.models import ConnectorCredentials
from app.connectors.exceptions import ConnectorConfigurationError
from app.connectors.registry.registry import ConnectorRegistry, default_registry


class ConnectorFactory:
    """
    Creates connector instances from the registry.

    Supports constructor dependency injection via `dependencies` and
    optional resolution of config/credentials from managers.
    """

    def __init__(
        self,
        registry: Optional[ConnectorRegistry] = None,
        credential_manager: Optional[CredentialManager] = None,
        default_dependencies: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.registry = registry or default_registry
        self.credential_manager = credential_manager
        self.default_dependencies = default_dependencies or {}

    def create(
        self,
        name: str,
        *,
        config: Optional[ConnectorConfig] = None,
        credentials: Optional[ConnectorCredentials] = None,
        load_credentials: bool = False,
        require_enabled: bool = True,
        **dependencies: Any,
    ) -> BaseConnector:
        """
        Instantiate a connector by registered name.

        Args:
            name: Registered connector key.
            config: Optional runtime configuration.
            credentials: Optional credentials override.
            load_credentials: If True, load from CredentialManager when
                credentials are not provided.
            require_enabled: Fail if the connector is disabled.
            **dependencies: Extra kwargs injected into the connector constructor.
        """
        connector_cls: Type[BaseConnector] = self.registry.get_class(
            name,
            require_enabled=require_enabled,
        )

        resolved_credentials = credentials
        if resolved_credentials is None and load_credentials:
            if self.credential_manager is None:
                raise ConnectorConfigurationError(
                    "load_credentials=True but no CredentialManager was "
                    "configured on the factory"
                )
            resolved_credentials = self.credential_manager.require(name)

        if config is not None and config.connector_name.lower() != name.strip().lower():
            raise ConnectorConfigurationError(
                "Config connector_name does not match requested connector",
                details={
                    "config_name": config.connector_name,
                    "requested": name,
                },
            )

        merged = {**self.default_dependencies, **dependencies}
        return connector_cls(
            config=config,
            credentials=resolved_credentials,
            **merged,
        )

    def create_from_class(
        self,
        connector_cls: Type[BaseConnector],
        *,
        config: Optional[ConnectorConfig] = None,
        credentials: Optional[ConnectorCredentials] = None,
        **dependencies: Any,
    ) -> BaseConnector:
        """Instantiate without registry lookup (useful in tests)."""
        merged = {**self.default_dependencies, **dependencies}
        return connector_cls(
            config=config,
            credentials=credentials,
            **merged,
        )

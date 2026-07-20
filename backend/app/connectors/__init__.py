"""
Connector Framework

Reusable plugin architecture for external integrations
(Jira, GitHub, AI providers, Playwright, etc.).

Provider packages are placeholders — implement in later milestones.
"""

from app.connectors.base import (
    BaseConnector,
    ConfigurationField,
    ConfigurationSchema,
    ConnectorCategory,
    ConnectorEnvironment,
    ConnectorHealth,
    ConnectorMetadata,
    CredentialType,
    HealthStatus,
)
from app.connectors.config import ConnectorConfig, ConnectorConfigManager
from app.connectors.credentials import (
    ConnectorCredentials,
    CredentialManager,
    InMemoryCredentialStore,
    TokenRefresher,
)
from app.connectors.exceptions import (
    ConnectorAlreadyRegisteredError,
    ConnectorConfigurationError,
    ConnectorConnectionError,
    ConnectorCredentialError,
    ConnectorDisabledError,
    ConnectorError,
    ConnectorHealthCheckError,
    ConnectorNotFoundError,
)
from app.connectors.factory import ConnectorFactory
from app.connectors.registry import (
    ConnectorRegistration,
    ConnectorRegistry,
    default_registry,
)

__all__ = [
    "BaseConnector",
    "ConfigurationField",
    "ConfigurationSchema",
    "ConnectorCategory",
    "ConnectorConfig",
    "ConnectorConfigManager",
    "ConnectorCredentials",
    "ConnectorEnvironment",
    "ConnectorFactory",
    "ConnectorHealth",
    "ConnectorMetadata",
    "ConnectorRegistration",
    "ConnectorRegistry",
    "CredentialManager",
    "CredentialType",
    "HealthStatus",
    "InMemoryCredentialStore",
    "TokenRefresher",
    "default_registry",
    "ConnectorError",
    "ConnectorNotFoundError",
    "ConnectorDisabledError",
    "ConnectorAlreadyRegisteredError",
    "ConnectorConfigurationError",
    "ConnectorCredentialError",
    "ConnectorConnectionError",
    "ConnectorHealthCheckError",
]

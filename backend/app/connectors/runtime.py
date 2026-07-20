"""
Shared connector runtime — process-wide registry, factory, and managers.

Providers register here at app startup. API layers resolve connectors via the factory.
"""

from app.connectors.config import ConnectorConfigManager
from app.connectors.credentials import CredentialManager, InMemoryCredentialStore
from app.connectors.factory import ConnectorFactory
from app.connectors.registry import ConnectorRegistry

connector_registry = ConnectorRegistry()
credential_manager = CredentialManager(store=InMemoryCredentialStore())
config_manager = ConnectorConfigManager()
connector_factory = ConnectorFactory(
    registry=connector_registry,
    credential_manager=credential_manager,
)


def register_builtin_connectors() -> None:
    """Register shipped connector plugins (idempotent)."""
    from app.connectors.github.connector import GitHubConnector
    from app.connectors.jira.connector import JiraConnector

    if not connector_registry.is_registered("jira"):
        connector_registry.register(JiraConnector)
    if not connector_registry.is_registered("github"):
        connector_registry.register(GitHubConnector)

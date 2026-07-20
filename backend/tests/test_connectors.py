"""
Unit tests for Connector Registry, Factory, and Credential Manager.
"""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.connectors import (
    BaseConnector,
    ConfigurationField,
    ConfigurationSchema,
    ConnectorAlreadyRegisteredError,
    ConnectorCategory,
    ConnectorConfig,
    ConnectorCredentials,
    ConnectorDisabledError,
    ConnectorFactory,
    ConnectorHealth,
    ConnectorMetadata,
    ConnectorNotFoundError,
    ConnectorRegistry,
    CredentialManager,
    CredentialType,
    HealthStatus,
    InMemoryCredentialStore,
)
from app.connectors.base.types import ConnectorEnvironment


class MockConnector(BaseConnector):
    """Test-only connector — not a production provider."""

    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            name="mock",
            display_name="Mock Connector",
            version="1.0.0",
            category=ConnectorCategory.OTHER,
            description="In-test connector for framework verification",
            supported_credential_types=[CredentialType.API_KEY],
            capabilities=["health_check"],
        )

    def configuration_schema(self) -> ConfigurationSchema:
        return ConfigurationSchema(
            schema_version="1.0",
            title="Mock Connector Config",
            fields=[
                ConfigurationField(
                    name="base_url",
                    required=True,
                    description="Mock base URL",
                )
            ],
        )

    async def validate_credentials(self) -> bool:
        return self.credentials is not None and self.credentials.api_key is not None

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def health_check(self) -> ConnectorHealth:
        return ConnectorHealth(
            status=HealthStatus.HEALTHY if self._connected else HealthStatus.UNHEALTHY,
            version=self.metadata().version,
            latency_ms=1.5,
            message="ok" if self._connected else "not connected",
        )


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class TestConnectorRegistry:
    def setup_method(self) -> None:
        self.registry = ConnectorRegistry()

    def test_register_and_get(self) -> None:
        self.registry.register(MockConnector)
        entry = self.registry.get("mock")
        assert entry.name == "mock"
        assert entry.connector_class is MockConnector
        assert entry.enabled is True
        assert "mock" in self.registry.list_names()

    def test_duplicate_registration_raises(self) -> None:
        self.registry.register(MockConnector)
        with pytest.raises(ConnectorAlreadyRegisteredError):
            self.registry.register(MockConnector)

    def test_overwrite_registration(self) -> None:
        self.registry.register(MockConnector)
        self.registry.register(MockConnector, overwrite=True)
        assert len(self.registry.list_installed()) == 1

    def test_enable_disable(self) -> None:
        self.registry.register(MockConnector)
        self.registry.disable("mock")
        assert self.registry.is_enabled("mock") is False
        with pytest.raises(ConnectorDisabledError):
            self.registry.get("mock")
        # Still resolvable when require_enabled=False
        assert self.registry.get("mock", require_enabled=False).enabled is False
        self.registry.enable("mock")
        assert self.registry.is_enabled("mock") is True

    def test_not_found(self) -> None:
        with pytest.raises(ConnectorNotFoundError):
            self.registry.get("missing")

    def test_list_enabled_only(self) -> None:
        self.registry.register(MockConnector)
        self.registry.disable("mock")
        assert self.registry.list_names(enabled_only=True) == []
        assert self.registry.list_names(enabled_only=False) == ["mock"]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


class TestConnectorFactory:
    def setup_method(self) -> None:
        self.registry = ConnectorRegistry()
        self.registry.register(MockConnector)
        self.credentials = CredentialManager(store=InMemoryCredentialStore())
        self.factory = ConnectorFactory(
            registry=self.registry,
            credential_manager=self.credentials,
            default_dependencies={"http_client": "shared-client"},
        )

    def test_create_injects_config_and_dependencies(self) -> None:
        config = ConnectorConfig(
            connector_name="mock",
            environment=ConnectorEnvironment.DEVELOPMENT,
            settings={"base_url": "https://example.test"},
        )
        connector = self.factory.create("mock", config=config)
        assert isinstance(connector, MockConnector)
        assert connector.config is config
        assert connector.dependencies["http_client"] == "shared-client"
        assert connector.get_config_value("base_url") == "https://example.test"

    def test_create_loads_credentials(self) -> None:
        creds = ConnectorCredentials(
            connector_name="mock",
            credential_type=CredentialType.API_KEY,
            api_key="secret-key",
        )
        self.credentials.save(creds)
        connector = self.factory.create("mock", load_credentials=True)
        assert connector.credentials is not None
        assert connector.credentials.get_secret_value("api_key") == "secret-key"

    def test_create_respects_disabled(self) -> None:
        self.registry.disable("mock")
        with pytest.raises(ConnectorDisabledError):
            self.factory.create("mock")

    def test_create_from_class(self) -> None:
        connector = self.factory.create_from_class(MockConnector)
        assert isinstance(connector, MockConnector)

    @pytest.mark.asyncio
    async def test_connector_lifecycle_health(self) -> None:
        connector = self.factory.create("mock")
        await connector.connect()
        health = await connector.health_check()
        assert health.status == HealthStatus.HEALTHY
        assert health.latency_ms == 1.5
        assert health.version == "1.0.0"
        assert health.last_checked is not None
        await connector.disconnect()
        assert connector.is_connected is False


# ---------------------------------------------------------------------------
# Credential Manager
# ---------------------------------------------------------------------------


class TestCredentialManager:
    def setup_method(self) -> None:
        self.manager = CredentialManager(store=InMemoryCredentialStore())

    def test_save_and_get_api_key(self) -> None:
        creds = ConnectorCredentials(
            connector_name="jira",
            credential_type=CredentialType.API_KEY,
            api_key="abc123",
        )
        self.manager.save(creds)
        loaded = self.manager.require("jira")
        assert loaded.credential_type == CredentialType.API_KEY
        assert loaded.get_secret_value("api_key") == "abc123"
        summary = loaded.masked_summary()
        assert summary["has_api_key"] is True
        assert "abc123" not in str(summary)

    def test_username_password(self) -> None:
        creds = ConnectorCredentials(
            connector_name="legacy",
            credential_type=CredentialType.USERNAME_PASSWORD,
            username="qa",
            password="secret",
        )
        self.manager.save(creds)
        assert self.manager.get("legacy") is not None

    def test_oauth_fields(self) -> None:
        creds = ConnectorCredentials(
            connector_name="oauth-app",
            credential_type=CredentialType.OAUTH,
            client_id="client",
            client_secret="secret",
            access_token="access",
            refresh_token="refresh",
            token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        self.manager.save(creds)
        assert creds.needs_token_refresh() is False

    def test_needs_token_refresh_when_expired(self) -> None:
        creds = ConnectorCredentials(
            connector_name="oauth-app",
            credential_type=CredentialType.OAUTH,
            client_id="client",
            client_secret="secret",
            token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        assert creds.needs_token_refresh() is True

    def test_missing_api_key_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ConnectorCredentials(
                connector_name="bad",
                credential_type=CredentialType.API_KEY,
            )

    def test_delete(self) -> None:
        self.manager.save(
            ConnectorCredentials(
                connector_name="tmp",
                credential_type=CredentialType.PAT,
                api_key="pat-token",
            )
        )
        assert self.manager.delete("tmp") is True
        assert self.manager.get("tmp") is None

    def test_supports_types(self) -> None:
        for ctype in CredentialType:
            assert self.manager.supports_type(ctype) is True

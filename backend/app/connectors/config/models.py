"""
Connector configuration models and manager.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.connectors.base.types import ConnectorEnvironment
from app.connectors.exceptions import ConnectorConfigurationError


class ConnectorConfig(BaseModel):
    """
    Versioned runtime configuration for a connector instance.

    `settings` holds provider-specific keys validated against
    the connector's configuration_schema() by ConnectorConfigManager.
    """

    connector_name: str
    config_version: str = "1.0"
    environment: ConnectorEnvironment = ConnectorEnvironment.DEVELOPMENT
    enabled: bool = True
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("connector_name")
    @classmethod
    def name_not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("connector_name must not be blank")
        return cleaned


class ConnectorConfigManager:
    """
    Validates, versions, and stores connector configurations in memory.

    Production deployments should swap the store for a DB / secrets-backed
    implementation without changing callers.
    """

    def __init__(self) -> None:
        self._configs: Dict[str, ConnectorConfig] = {}

    def save(self, config: ConnectorConfig) -> ConnectorConfig:
        """Persist (or replace) a configuration by connector name + environment."""
        key = self._key(config.connector_name, config.environment)
        updated = config.model_copy(
            update={"updated_at": datetime.now(timezone.utc)}
        )
        self._configs[key] = updated
        return updated

    def get(
        self,
        connector_name: str,
        environment: ConnectorEnvironment = ConnectorEnvironment.DEVELOPMENT,
    ) -> Optional[ConnectorConfig]:
        return self._configs.get(self._key(connector_name, environment))

    def delete(
        self,
        connector_name: str,
        environment: ConnectorEnvironment = ConnectorEnvironment.DEVELOPMENT,
    ) -> bool:
        key = self._key(connector_name, environment)
        return self._configs.pop(key, None) is not None

    def list(
        self,
        environment: Optional[ConnectorEnvironment] = None,
    ) -> List[ConnectorConfig]:
        values = list(self._configs.values())
        if environment is None:
            return values
        return [c for c in values if c.environment == environment]

    def validate_against_schema(
        self,
        config: ConnectorConfig,
        required_fields: List[str],
    ) -> None:
        """
        Ensure required settings keys are present and non-empty.

        Full JSON-Schema validation can be layered later; this keeps the
        framework lightweight and provider-agnostic.
        """
        missing = [
            field
            for field in required_fields
            if field not in config.settings
            or config.settings[field] in (None, "")
        ]
        if missing:
            raise ConnectorConfigurationError(
                f"Missing required configuration fields: {', '.join(missing)}",
                details={"missing": missing, "connector": config.connector_name},
            )

    @staticmethod
    def _key(connector_name: str, environment: ConnectorEnvironment) -> str:
        return f"{connector_name}:{environment.value}"

"""
Connector Registry — dynamic registration and discovery of plugins.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Type

from app.connectors.base.connector import BaseConnector
from app.connectors.base.types import ConnectorMetadata
from app.connectors.exceptions import (
    ConnectorAlreadyRegisteredError,
    ConnectorDisabledError,
    ConnectorNotFoundError,
)


@dataclass
class ConnectorRegistration:
    """Bookkeeping entry for a registered connector class."""

    name: str
    connector_class: Type[BaseConnector]
    enabled: bool = True
    metadata: Optional[ConnectorMetadata] = field(default=None, repr=False)

    def resolve_metadata(self) -> ConnectorMetadata:
        if self.metadata is not None:
            return self.metadata
        # Instantiate lightly without config to read static metadata
        return self.connector_class().metadata()


class ConnectorRegistry:
    """
    Process-wide registry of connector plugins.

    Connectors register their class; the Factory instantiates instances.
    """

    def __init__(self) -> None:
        self._entries: Dict[str, ConnectorRegistration] = {}

    def register(
        self,
        connector_class: Type[BaseConnector],
        *,
        name: Optional[str] = None,
        enabled: bool = True,
        overwrite: bool = False,
    ) -> ConnectorRegistration:
        """Register a connector class dynamically."""
        instance_meta = connector_class().metadata()
        key = (name or instance_meta.name).strip().lower()
        if not key:
            raise ValueError("Connector name must not be blank")
        if key in self._entries and not overwrite:
            raise ConnectorAlreadyRegisteredError(key)

        registration = ConnectorRegistration(
            name=key,
            connector_class=connector_class,
            enabled=enabled,
            metadata=instance_meta,
        )
        self._entries[key] = registration
        return registration

    def unregister(self, name: str) -> bool:
        return self._entries.pop(name.strip().lower(), None) is not None

    def get(self, name: str, *, require_enabled: bool = True) -> ConnectorRegistration:
        key = name.strip().lower()
        entry = self._entries.get(key)
        if entry is None:
            raise ConnectorNotFoundError(key)
        if require_enabled and not entry.enabled:
            raise ConnectorDisabledError(key)
        return entry

    def get_class(self, name: str, *, require_enabled: bool = True) -> Type[BaseConnector]:
        return self.get(name, require_enabled=require_enabled).connector_class

    def list_installed(self, *, enabled_only: bool = False) -> List[ConnectorRegistration]:
        entries = list(self._entries.values())
        if enabled_only:
            return [e for e in entries if e.enabled]
        return entries

    def list_names(self, *, enabled_only: bool = False) -> List[str]:
        return [e.name for e in self.list_installed(enabled_only=enabled_only)]

    def enable(self, name: str) -> None:
        entry = self.get(name, require_enabled=False)
        entry.enabled = True

    def disable(self, name: str) -> None:
        entry = self.get(name, require_enabled=False)
        entry.enabled = False

    def is_registered(self, name: str) -> bool:
        return name.strip().lower() in self._entries

    def is_enabled(self, name: str) -> bool:
        entry = self._entries.get(name.strip().lower())
        return bool(entry and entry.enabled)

    def clear(self) -> None:
        """Remove all registrations (primarily for tests)."""
        self._entries.clear()


# Default singleton used by the factory unless overridden (DI-friendly).
default_registry = ConnectorRegistry()

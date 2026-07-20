"""
Credential Manager — secure storage abstraction for connector secrets.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional, Protocol

from app.connectors.base.types import CredentialType
from app.connectors.credentials.models import ConnectorCredentials
from app.connectors.exceptions import ConnectorCredentialError


class CredentialStore(Protocol):
    """Storage backend protocol (in-memory, vault, KMS, etc.)."""

    def put(self, key: str, credentials: ConnectorCredentials) -> None: ...

    def get(self, key: str) -> Optional[ConnectorCredentials]: ...

    def delete(self, key: str) -> bool: ...

    def keys(self) -> List[str]: ...


class InMemoryCredentialStore:
    """
    Process-local credential store for development and unit tests.

    NOT for production secrets. Replace with a vault-backed store.
    """

    def __init__(self) -> None:
        self._data: Dict[str, ConnectorCredentials] = {}

    def put(self, key: str, credentials: ConnectorCredentials) -> None:
        self._data[key] = credentials

    def get(self, key: str) -> Optional[ConnectorCredentials]:
        return self._data.get(key)

    def delete(self, key: str) -> bool:
        return self._data.pop(key, None) is not None

    def keys(self) -> List[str]:
        return list(self._data.keys())


class TokenRefresher(ABC):
    """
    Future-ready hook for OAuth / rotating PAT refresh.

    Providers implement this when they support refresh_token flows.
    """

    @abstractmethod
    async def refresh(self, credentials: ConnectorCredentials) -> ConnectorCredentials:
        """Return updated credentials with a fresh access_token."""


class CredentialManager:
    """
    Manages connector credentials with pluggable storage.

    Supports API Key, OAuth, Username/Password, PAT, and bearer tokens.
    Token refresh is delegated to an optional TokenRefresher.
    """

    def __init__(
        self,
        store: Optional[CredentialStore] = None,
        token_refresher: Optional[TokenRefresher] = None,
    ) -> None:
        self._store: CredentialStore = store or InMemoryCredentialStore()
        self._token_refresher = token_refresher

    def save(self, credentials: ConnectorCredentials) -> ConnectorCredentials:
        """Validate and store credentials for a connector."""
        updated = credentials.model_copy(
            update={"updated_at": datetime.now(timezone.utc)}
        )
        self._store.put(credentials.connector_name, updated)
        return updated

    def get(self, connector_name: str) -> Optional[ConnectorCredentials]:
        return self._store.get(connector_name)

    def require(self, connector_name: str) -> ConnectorCredentials:
        credentials = self.get(connector_name)
        if credentials is None:
            raise ConnectorCredentialError(
                f"No credentials stored for connector '{connector_name}'",
                details={"connector": connector_name},
            )
        return credentials

    def delete(self, connector_name: str) -> bool:
        return self._store.delete(connector_name)

    def list_names(self) -> List[str]:
        return self._store.keys()

    def supports_type(self, credential_type: CredentialType) -> bool:
        return credential_type in set(CredentialType)

    async def refresh_if_needed(
        self,
        connector_name: str,
    ) -> ConnectorCredentials:
        """
        Refresh OAuth/PAT tokens when expired, if a TokenRefresher is configured.
        """
        credentials = self.require(connector_name)
        if not credentials.needs_token_refresh():
            return credentials
        if self._token_refresher is None:
            raise ConnectorCredentialError(
                f"Credentials for '{connector_name}' are expired and no TokenRefresher is configured",
                details={"connector": connector_name},
            )
        refreshed = await self._token_refresher.refresh(credentials)
        return self.save(refreshed)

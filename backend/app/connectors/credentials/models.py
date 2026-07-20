"""
Credential models for the connector framework.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, SecretStr, model_validator

from app.connectors.base.types import CredentialType


class ConnectorCredentials(BaseModel):
    """
    Credential payload for a connector.

    Secrets use SecretStr so they are not leaked via repr/logs.
    Token refresh fields are future-ready (OAuth / rotating PAT).
    """

    connector_name: str
    credential_type: CredentialType
    # API key / PAT / bearer
    api_key: Optional[SecretStr] = None
    # Username / password
    username: Optional[str] = None
    password: Optional[SecretStr] = None
    # OAuth
    client_id: Optional[str] = None
    client_secret: Optional[SecretStr] = None
    access_token: Optional[SecretStr] = None
    refresh_token: Optional[SecretStr] = None
    token_expires_at: Optional[datetime] = None
    # Extensibility
    extra: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_required_fields(self) -> "ConnectorCredentials":
        ctype = self.credential_type
        if ctype == CredentialType.API_KEY and not self.api_key:
            raise ValueError("api_key is required for API_KEY credentials")
        if ctype == CredentialType.PAT and not self.api_key:
            raise ValueError("api_key (PAT) is required for PAT credentials")
        if ctype == CredentialType.BEARER_TOKEN and not self.access_token and not self.api_key:
            raise ValueError(
                "access_token or api_key is required for BEARER_TOKEN credentials"
            )
        if ctype == CredentialType.USERNAME_PASSWORD:
            if not self.username or not self.password:
                raise ValueError(
                    "username and password are required for USERNAME_PASSWORD credentials"
                )
        if ctype == CredentialType.OAUTH:
            if not self.client_id or not self.client_secret:
                raise ValueError(
                    "client_id and client_secret are required for OAUTH credentials"
                )
        return self

    def get_secret_value(self, field: str) -> Optional[str]:
        """Return the plaintext secret for a named field (use sparingly)."""
        value = getattr(self, field, None)
        if isinstance(value, SecretStr):
            return value.get_secret_value()
        if isinstance(value, str):
            return value
        return None

    def needs_token_refresh(self, *, now: Optional[datetime] = None) -> bool:
        """Future-ready helper for OAuth / rotating tokens."""
        if self.token_expires_at is None:
            return False
        current = now or datetime.now(timezone.utc)
        return current >= self.token_expires_at

    def masked_summary(self) -> Dict[str, Any]:
        """Safe diagnostic view — never includes secret values."""
        return {
            "connector_name": self.connector_name,
            "credential_type": self.credential_type.value,
            "has_api_key": self.api_key is not None,
            "has_password": self.password is not None,
            "has_access_token": self.access_token is not None,
            "has_refresh_token": self.refresh_token is not None,
            "username": self.username,
            "client_id": self.client_id,
            "token_expires_at": (
                self.token_expires_at.isoformat() if self.token_expires_at else None
            ),
        }

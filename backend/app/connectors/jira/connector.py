"""
Jira Cloud Connector — implements BaseConnector for Jira Cloud REST API v3.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.connectors.base.connector import BaseConnector
from app.connectors.base.types import (
    ConfigurationField,
    ConfigurationSchema,
    ConnectorCategory,
    ConnectorHealth,
    ConnectorMetadata,
    CredentialType,
    HealthStatus,
)
from app.connectors.exceptions import (
    ConnectorConnectionError,
    ConnectorCredentialError,
)
from app.connectors.jira.client import JiraClient
from app.connectors.jira.constants import ISSUE_FIELDS, JIRA_CONNECTOR_NAME


class JiraConnector(BaseConnector):
    """
    Jira Cloud connector.

    Auth: email + API token (stored as USERNAME_PASSWORD in CredentialManager).
    Config settings:
      - base_url (required): https://your-domain.atlassian.net
      - acceptance_criteria_field (optional): customfield_XXXXX
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._client: Optional[JiraClient] = None

    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            name=JIRA_CONNECTOR_NAME,
            display_name="Jira Cloud",
            version="1.0.0",
            category=ConnectorCategory.ISSUE_TRACKER,
            description="Atlassian Jira Cloud REST API v3 connector",
            provider="Atlassian",
            homepage="https://developer.atlassian.com/cloud/jira/platform/rest/v3/",
            capabilities=[
                "connect",
                "health_check",
                "list_projects",
                "list_boards",
                "list_sprints",
                "sync_issues",
                "create_issue",
            ],
            supported_credential_types=[CredentialType.USERNAME_PASSWORD],
            config_schema_version="1.0",
        )

    def configuration_schema(self) -> ConfigurationSchema:
        return ConfigurationSchema(
            schema_version="1.0",
            title="Jira Cloud Configuration",
            description="Connection settings for Jira Cloud",
            fields=[
                ConfigurationField(
                    name="base_url",
                    field_type="string",
                    required=True,
                    description="Jira Cloud site URL, e.g. https://acme.atlassian.net",
                ),
                ConfigurationField(
                    name="acceptance_criteria_field",
                    field_type="string",
                    required=False,
                    description="Optional custom field id for Acceptance Criteria",
                ),
            ],
        )

    def _build_client(self) -> JiraClient:
        if self.credentials is None:
            raise ConnectorCredentialError("Jira credentials are not configured")
        email = self.credentials.username
        token = self.credentials.get_secret_value("password")
        base_url = self.get_config_value("base_url")
        if not email or not token:
            raise ConnectorCredentialError(
                "Jira requires email (username) and API token (password)"
            )
        if not base_url:
            raise ConnectorCredentialError(
                "Jira config requires base_url",
                details={"field": "base_url"},
            )
        return JiraClient(base_url=str(base_url), email=email, api_token=token)

    @property
    def client(self) -> JiraClient:
        if self._client is None:
            raise ConnectorConnectionError("Jira connector is not connected")
        return self._client

    async def validate_credentials(self) -> bool:
        if self.credentials is None:
            return False
        if self.credentials.credential_type != CredentialType.USERNAME_PASSWORD:
            return False
        if not self.credentials.username or not self.credentials.password:
            return False
        if not self.get_config_value("base_url"):
            return False
        return True

    async def connect(self) -> None:
        if not await self.validate_credentials():
            raise ConnectorCredentialError(
                "Invalid Jira credentials or configuration"
            )
        self._client = self._build_client()
        await self._client.open()
        # Prove auth works
        await self._client.get_myself()
        self._connected = True

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None
        self._connected = False

    async def health_check(self) -> ConnectorHealth:
        try:
            if not self._connected or self._client is None:
                self._client = self._build_client()
                await self._client.open()
            me, latency_ms = await self.client.timed_myself()
            server = await self.client.get_server_info()
            self._connected = True
            return ConnectorHealth(
                status=HealthStatus.HEALTHY,
                version=str(server.get("version") or self.metadata().version),
                latency_ms=round(latency_ms, 2),
                message=f"Authenticated as {me.get('displayName') or me.get('emailAddress')}",
                details={
                    "account_id": me.get("accountId"),
                    "base_url": self.get_config_value("base_url"),
                },
            )
        except Exception as exc:  # noqa: BLE001 — mapped to health status
            return ConnectorHealth(
                status=HealthStatus.UNHEALTHY,
                version=self.metadata().version,
                message=str(exc),
            )

    # ----- Domain helpers used by sync / API layer -----

    async def list_projects(self) -> List[Dict[str, Any]]:
        return await self.client.list_projects()

    async def list_boards(
        self,
        project_key_or_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return await self.client.list_boards(project_key_or_id=project_key_or_id)

    async def list_sprints(
        self,
        board_id: int | str,
        *,
        state: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        return await self.client.list_sprints(board_id, state=state)

    def issue_fields(self) -> List[str]:
        fields = list(ISSUE_FIELDS)
        ac_field = self.get_config_value("acceptance_criteria_field")
        if ac_field and ac_field not in fields:
            fields.append(str(ac_field))
        return fields

    async def create_issue(
        self,
        *,
        project_key: str,
        summary: str,
        description: Optional[str] = None,
        issue_type: str = "Bug",
        priority_name: Optional[str] = None,
        labels: Optional[List[str]] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a Jira issue (Bug by default) via the REST client."""
        return await self.client.create_issue(
            project_key=project_key,
            summary=summary,
            description=description,
            issue_type=issue_type,
            priority_name=priority_name,
            labels=labels,
            extra_fields=extra_fields,
        )

"""
Jira connector application service — connect / disconnect / health via framework.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from app.connectors.base.types import (
    ConnectorEnvironment,
    CredentialType,
    HealthStatus,
)
from app.connectors.config.models import ConnectorConfig
from app.connectors.credentials.models import ConnectorCredentials
from app.connectors.exceptions import (
    ConnectorConnectionError,
    ConnectorCredentialError,
    ConnectorDisabledError,
    ConnectorNotFoundError,
)
from app.connectors.jira.connector import JiraConnector
from app.connectors.jira.constants import JIRA_CONNECTOR_NAME
from app.connectors.runtime import (
    config_manager,
    connector_factory,
    credential_manager,
)
from app.core.exceptions import BadRequestException, ServiceUnavailableException
from app.schemas.jira import (
    JiraBoardItem,
    JiraConnectRequest,
    JiraConnectResponse,
    JiraHealthResponse,
    JiraMessageResponse,
    JiraProjectItem,
    JiraSprintItem,
)


class JiraConnectorService:
    """Facade over Connector Framework for Jira Cloud operations."""

    def _get_connector(self, *, require_connected: bool = False) -> JiraConnector:
        try:
            config = config_manager.get(JIRA_CONNECTOR_NAME)
            connector = connector_factory.create(
                JIRA_CONNECTOR_NAME,
                config=config,
                load_credentials=True,
            )
        except ConnectorNotFoundError as exc:
            raise ServiceUnavailableException(
                "Jira connector is not registered",
                service="jira",
            ) from exc
        except ConnectorDisabledError as exc:
            raise ServiceUnavailableException(
                "Jira connector is disabled",
                service="jira",
            ) from exc
        except ConnectorCredentialError as exc:
            raise BadRequestException(
                "Jira is not connected — call POST /connectors/jira/connect first",
                details=exc.details,
            ) from exc

        assert isinstance(connector, JiraConnector)
        if require_connected and not connector.is_connected:
            # Lazy connect for read APIs
            return connector
        return connector

    async def connect(self, payload: JiraConnectRequest) -> JiraConnectResponse:
        base_url = payload.base_url.strip().rstrip("/")
        if not base_url.startswith("https://"):
            raise BadRequestException("base_url must be an https:// Jira Cloud URL")

        settings = {"base_url": base_url}
        if payload.acceptance_criteria_field:
            settings["acceptance_criteria_field"] = payload.acceptance_criteria_field

        config = ConnectorConfig(
            connector_name=JIRA_CONNECTOR_NAME,
            environment=ConnectorEnvironment.DEVELOPMENT,
            settings=settings,
            enabled=True,
        )
        config_manager.save(config)

        credentials = ConnectorCredentials(
            connector_name=JIRA_CONNECTOR_NAME,
            credential_type=CredentialType.USERNAME_PASSWORD,
            username=payload.email.strip(),
            password=payload.api_token,
        )
        credential_manager.save(credentials)

        connector = connector_factory.create(
            JIRA_CONNECTOR_NAME,
            config=config,
            credentials=credentials,
        )
        assert isinstance(connector, JiraConnector)

        try:
            await connector.connect()
            health = await connector.health_check()
        except (ConnectorCredentialError, ConnectorConnectionError) as exc:
            await connector.disconnect()
            raise BadRequestException(
                f"Failed to connect to Jira: {exc.message}",
                details=exc.details,
            ) from exc

        display = None
        if health.details:
            display = health.message
        return JiraConnectResponse(
            connected=True,
            message="Connected to Jira Cloud successfully",
            account_display_name=display,
            base_url=base_url,
        )

    async def disconnect(self) -> JiraMessageResponse:
        config = config_manager.get(JIRA_CONNECTOR_NAME)
        try:
            connector = connector_factory.create(
                JIRA_CONNECTOR_NAME,
                config=config,
                load_credentials=True,
                require_enabled=False,
            )
            assert isinstance(connector, JiraConnector)
            await connector.disconnect()
        except Exception:
            pass

        credential_manager.delete(JIRA_CONNECTOR_NAME)
        if config:
            config_manager.delete(JIRA_CONNECTOR_NAME, config.environment)

        return JiraMessageResponse(
            success=True,
            message="Disconnected from Jira Cloud",
        )

    async def health(self) -> JiraHealthResponse:
        connector = self._get_connector()
        try:
            if not connector.is_connected:
                await connector.connect()
            result = await connector.health_check()
        except Exception as exc:  # noqa: BLE001
            return JiraHealthResponse(
                status=HealthStatus.UNHEALTHY.value,
                version=connector.metadata().version,
                latency_ms=None,
                last_checked=datetime.now(timezone.utc),
                message=str(exc),
                details={},
            )

        return JiraHealthResponse(
            status=result.status.value,
            version=result.version,
            latency_ms=result.latency_ms,
            last_checked=result.last_checked,
            message=result.message,
            details=result.details,
        )

    async def list_projects(self) -> List[JiraProjectItem]:
        connector = self._get_connector()
        if not connector.is_connected:
            await connector.connect()
        projects = await connector.list_projects()
        return [
            JiraProjectItem(
                id=str(p.get("id")),
                key=p.get("key") or "",
                name=p.get("name") or "",
                style=p.get("style"),
                project_type_key=p.get("projectTypeKey"),
            )
            for p in projects
        ]

    async def list_boards(
        self,
        project_key: Optional[str] = None,
    ) -> List[JiraBoardItem]:
        connector = self._get_connector()
        if not connector.is_connected:
            await connector.connect()
        boards = await connector.list_boards(project_key_or_id=project_key)
        items: List[JiraBoardItem] = []
        for b in boards:
            location = b.get("location") or {}
            items.append(
                JiraBoardItem(
                    id=str(b.get("id")),
                    name=b.get("name") or "",
                    type=b.get("type"),
                    project_key=location.get("projectKey"),
                )
            )
        return items

    async def list_sprints(self, board_id: str) -> List[JiraSprintItem]:
        if not board_id:
            raise BadRequestException("board_id is required")
        connector = self._get_connector()
        if not connector.is_connected:
            await connector.connect()
        sprints = await connector.list_sprints(board_id)
        return [
            JiraSprintItem(
                id=str(s.get("id")),
                name=s.get("name") or "",
                state=s.get("state"),
                start_date=s.get("startDate"),
                end_date=s.get("endDate"),
                goal=s.get("goal"),
            )
            for s in sprints
        ]

    def get_connected_connector(self) -> JiraConnector:
        connector = self._get_connector()
        return connector

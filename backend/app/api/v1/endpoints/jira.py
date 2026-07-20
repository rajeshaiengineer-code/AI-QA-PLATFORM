"""
Jira Cloud Connector API endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import ErrorResponse
from app.schemas.jira import (
    JiraBoardItem,
    JiraConnectRequest,
    JiraConnectResponse,
    JiraHealthResponse,
    JiraMessageResponse,
    JiraProjectItem,
    JiraSprintItem,
    JiraSyncRequest,
    JiraSyncResponse,
)
from app.services.jira_connector import JiraConnectorService
from app.services.jira_sync import JiraSyncService

router = APIRouter()


def get_jira_service() -> JiraConnectorService:
    return JiraConnectorService()


@router.post(
    "/connect",
    response_model=JiraConnectResponse,
    status_code=status.HTTP_200_OK,
    summary="Connect to Jira Cloud",
    description=(
        "Validate and store Jira Cloud credentials (email + API token) "
        "via the Connector Framework Credential Manager, then open a session."
    ),
    responses={400: {"model": ErrorResponse}},
)
async def connect_jira(
    payload: JiraConnectRequest,
    service: JiraConnectorService = Depends(get_jira_service),
) -> JiraConnectResponse:
    return await service.connect(payload)


@router.post(
    "/disconnect",
    response_model=JiraMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Disconnect from Jira Cloud",
    description="Close the Jira session and remove stored credentials/config.",
)
async def disconnect_jira(
    service: JiraConnectorService = Depends(get_jira_service),
) -> JiraMessageResponse:
    return await service.disconnect()


@router.get(
    "/health",
    response_model=JiraHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Jira connector health check",
    description="Returns status, version, latency_ms, and last_checked.",
    responses={400: {"model": ErrorResponse}},
)
async def jira_health(
    service: JiraConnectorService = Depends(get_jira_service),
) -> JiraHealthResponse:
    return await service.health()


@router.get(
    "/projects",
    response_model=List[JiraProjectItem],
    status_code=status.HTTP_200_OK,
    summary="List Jira projects",
    description="List projects accessible to the connected Jira account (paginated upstream).",
    responses={400: {"model": ErrorResponse}},
)
async def list_jira_projects(
    service: JiraConnectorService = Depends(get_jira_service),
) -> List[JiraProjectItem]:
    return await service.list_projects()


@router.get(
    "/boards",
    response_model=List[JiraBoardItem],
    status_code=status.HTTP_200_OK,
    summary="List Jira boards",
    description="List Agile boards, optionally filtered by project key.",
    responses={400: {"model": ErrorResponse}},
)
async def list_jira_boards(
    project_key: Optional[str] = Query(
        None,
        description="Optional Jira project key or id",
    ),
    service: JiraConnectorService = Depends(get_jira_service),
) -> List[JiraBoardItem]:
    return await service.list_boards(project_key=project_key)


@router.get(
    "/sprints",
    response_model=List[JiraSprintItem],
    status_code=status.HTTP_200_OK,
    summary="List Jira sprints",
    description="List sprints for a Jira Agile board.",
    responses={400: {"model": ErrorResponse}},
)
async def list_jira_sprints(
    board_id: str = Query(..., description="Jira board id"),
    service: JiraConnectorService = Depends(get_jira_service),
) -> List[JiraSprintItem]:
    return await service.list_sprints(board_id)


@router.post(
    "/sync",
    response_model=JiraSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync Jira into the platform",
    description=(
        "Import the active sprint's stories (default), plus project metadata. "
        "Uses JQL ``sprint in openSprints()``. Set ``active_sprint_only=false`` "
        "to import the full project backlog. Preserves Jira ids and skips "
        "unchanged issues via update detection. Writes a SyncHistory record."
    ),
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def sync_jira(
    payload: JiraSyncRequest,
    db: AsyncSession = Depends(get_db),
    service: JiraConnectorService = Depends(get_jira_service),
) -> JiraSyncResponse:
    connector = service.get_connected_connector()
    if not connector.is_connected:
        await connector.connect()
    sync_service = JiraSyncService(db, connector)
    history = await sync_service.sync(
        organization_id=payload.organization_id,
        project_keys=payload.project_keys,
        board_id=payload.board_id,
        active_sprint_only=payload.active_sprint_only,
    )
    return JiraSyncResponse.model_validate(history)

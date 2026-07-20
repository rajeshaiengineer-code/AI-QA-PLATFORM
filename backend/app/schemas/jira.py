"""
Pydantic schemas for Jira connector APIs.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import ConfigDict, Field

from app.schemas.base import BaseSchema


class JiraConnectRequest(BaseSchema):
    """Connect / save Jira Cloud credentials + site URL."""

    base_url: str = Field(
        ...,
        examples=["https://your-domain.atlassian.net"],
        description="Jira Cloud site URL",
    )
    email: str = Field(..., examples=["qa@example.com"])
    api_token: str = Field(..., min_length=8, description="Atlassian API token")
    acceptance_criteria_field: Optional[str] = Field(
        None,
        description="Optional custom field id for Acceptance Criteria",
        examples=["customfield_10036"],
    )


class JiraConnectResponse(BaseSchema):
    connected: bool
    message: str
    account_display_name: Optional[str] = None
    base_url: Optional[str] = None


class JiraHealthResponse(BaseSchema):
    status: str
    version: Optional[str] = None
    latency_ms: Optional[float] = None
    last_checked: datetime
    message: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class JiraProjectItem(BaseSchema):
    id: str
    key: str
    name: str
    style: Optional[str] = None
    project_type_key: Optional[str] = None


class JiraBoardItem(BaseSchema):
    id: str
    name: str
    type: Optional[str] = None
    project_key: Optional[str] = None


class JiraSprintItem(BaseSchema):
    id: str
    name: str
    state: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    goal: Optional[str] = None


class JiraSyncRequest(BaseSchema):
    organization_id: UUID = Field(
        ...,
        description="Platform organization that will own imported projects",
    )
    project_keys: Optional[List[str]] = Field(
        None,
        description="Optional Jira project keys to sync (default: all accessible)",
    )
    board_id: Optional[str] = Field(
        None,
        description="Optional Agile board id to scope sprint import",
    )
    active_sprint_only: bool = Field(
        True,
        description=(
            "When true (default), import only issues in the current active "
            "sprint (JQL: sprint in openSprints())."
        ),
    )


class JiraSyncResponse(BaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    connector_name: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    projects_synced: int
    sprints_synced: int
    stories_created: int
    stories_updated: int
    stories_skipped: int
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class JiraMessageResponse(BaseSchema):
    success: bool = True
    message: str

"""
Bug / Jira Bug Creation Pydantic Schemas
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import ConfigDict, Field

from app.models.enums import BugStatus, Priority
from app.schemas.base import BaseSchema


class CreateJiraBugRequest(BaseSchema):
    """Create a Jira Bug from a failed execution (+ optional analysis)."""

    jira_project_key: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Jira project key where the Bug issue will be created.",
        examples=["QA", "PAY"],
    )
    failure_analysis_id: Optional[UUID] = Field(
        None,
        description=(
            "Optional FailureAnalysis id. Defaults to the latest analysis "
            "for the execution when omitted."
        ),
    )
    title: Optional[str] = Field(
        None,
        max_length=500,
        description="Override bug title (defaults to analysis/execution summary).",
    )
    description: Optional[str] = Field(
        None,
        description="Override bug description body.",
    )
    priority: Optional[Priority] = Field(
        None,
        description="Local + Jira priority (default: medium).",
    )
    issue_type: str = Field(
        "Bug",
        min_length=1,
        max_length=50,
        description="Jira issue type name (default: Bug).",
    )
    logs_url: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional logs link stored in bug metadata.",
    )
    execution_url: Optional[str] = Field(
        None,
        max_length=1000,
        description="Optional execution detail link stored in bug metadata.",
    )
    labels: Optional[List[str]] = Field(
        None,
        description="Optional Jira labels.",
    )


class BugResponse(BaseSchema):
    """Persisted local Bug (optionally synced to Jira via external_id)."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440030",
                "project_id": "550e8400-e29b-41d4-a716-446655440001",
                "story_id": "550e8400-e29b-41d4-a716-446655440000",
                "test_case_id": "550e8400-e29b-41d4-a716-446655440011",
                "execution_id": "550e8400-e29b-41d4-a716-446655440015",
                "failure_analysis_id": "550e8400-e29b-41d4-a716-446655440020",
                "title": "[Auto] Login fails on empty password",
                "description": "Root cause: missing validation...",
                "status": "open",
                "priority": "high",
                "external_id": "QA-42",
                "extra_metadata": {
                    "summary": "Login fails...",
                    "logs_url": "stub://logs/run-1.txt",
                    "execution_url": "/api/v1/executions/...",
                    "jira_url": "https://acme.atlassian.net/browse/QA-42",
                },
                "created_at": "2026-07-16T00:00:00Z",
                "updated_at": "2026-07-16T00:00:00Z",
                "is_deleted": False,
                "version": 1,
            }
        },
    )

    id: UUID
    project_id: UUID
    story_id: Optional[UUID] = None
    test_case_id: Optional[UUID] = None
    execution_id: Optional[UUID] = None
    failure_analysis_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    status: BugStatus
    priority: Priority
    external_id: Optional[str] = None
    extra_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None
    updated_by: Optional[UUID] = None
    is_deleted: bool = False
    version: int = 1


class CreateJiraBugResponse(BaseSchema):
    """Result of creating a Jira bug and persisting the local Bug row."""

    bug: BugResponse
    jira_key: str
    jira_id: Optional[str] = None
    jira_url: Optional[str] = None

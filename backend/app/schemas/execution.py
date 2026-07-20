"""
Pydantic schemas for the Execution Engine APIs.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import Field, model_validator

from app.models.enums import AutomationStatus, ExecutionStatus
from app.schemas.base import BaseSchema, PaginatedResponse, TimestampSchema


class ExecutionRunRequest(BaseSchema):
    """
    Trigger a test run (stub by default, or local Playwright).

    Provide exactly one of: ``story_id``, ``automation_artifact_id``,
    or ``automation_job_id``.
    """

    story_id: Optional[UUID] = Field(
        None,
        description="Run approved (or all) test cases for this story",
    )
    automation_artifact_id: Optional[UUID] = Field(
        None,
        description="Run using artifact source test cases / story",
    )
    automation_job_id: Optional[UUID] = Field(
        None,
        description="Run (or re-run) an existing automation job",
    )
    workflow_run_id: Optional[UUID] = Field(
        None,
        description=(
            "Optional workflow run id — emits ExecutionStarted / "
            "ExecutionCompleted when provided"
        ),
    )
    include_drafts: bool = Field(
        False,
        description="When resolving from story, include non-approved cases",
    )
    force_fail_test_case_ids: Optional[List[UUID]] = Field(
        None,
        description="Stub runner: force these case ids to fail",
    )
    runner: Literal["stub", "playwright"] = Field(
        "stub",
        description="Execution backend: stub (default) or local Playwright CLI",
    )
    name: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional job name override",
    )
    config: Optional[Dict[str, Any]] = Field(
        None,
        description="Extra runner/job config merged into AutomationJob.config",
    )

    @model_validator(mode="after")
    def _exactly_one_target(self) -> "ExecutionRunRequest":
        targets = [
            self.story_id,
            self.automation_artifact_id,
            self.automation_job_id,
        ]
        provided = sum(1 for t in targets if t is not None)
        if provided != 1:
            raise ValueError(
                "Provide exactly one of story_id, automation_artifact_id, "
                "or automation_job_id"
            )
        return self


class ExecutionResponse(TimestampSchema):
    """Single test-case execution result."""

    id: UUID
    automation_job_id: UUID
    test_case_id: UUID
    status: ExecutionStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    evidence_url: Optional[str] = None
    retry_count: int = 0
    version: int = 1


class AutomationJobSummary(TimestampSchema):
    """Automation job without nested executions (for list/detail embeds)."""

    id: UUID
    project_id: UUID
    sprint_id: Optional[UUID] = None
    name: str
    status: AutomationStatus
    triggered_by: Optional[UUID] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    config: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    version: int = 1


class AutomationJobResponse(AutomationJobSummary):
    """Automation job with nested execution results."""

    executions: List[ExecutionResponse] = Field(default_factory=list)
    passed: int = 0
    failed: int = 0
    error: int = 0
    skipped: int = 0
    total: int = 0


class ExecutionRunResponse(BaseSchema):
    """Result of POST /executions/run."""

    job: AutomationJobResponse
    workflow_run_id: Optional[UUID] = None
    runner: str = "stub"


class ExecutionDetailResponse(ExecutionResponse):
    """GET /executions/{id} with optional job summary."""

    automation_job: Optional[AutomationJobSummary] = None


ExecutionListResponse = PaginatedResponse[ExecutionResponse]
AutomationJobListResponse = PaginatedResponse[AutomationJobSummary]

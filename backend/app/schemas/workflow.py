"""Workflow API schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import Field

from app.orchestration.state.enums import WorkflowState
from app.schemas.base import BaseSchema


class WorkflowStartRequest(BaseSchema):
    story_id: UUID
    mark_synced: bool = True
    max_retries: int = Field(default=3, ge=0, le=20)


class WorkflowApproveRequest(BaseSchema):
    approved: bool = True
    reason: Optional[str] = None


class WorkflowRetryRequest(BaseSchema):
    from_state: WorkflowState


class WorkflowCancelRequest(BaseSchema):
    reason: str = Field(..., min_length=1, max_length=1000)


class WorkflowLogItem(BaseSchema):
    id: UUID
    level: str
    event_type: Optional[str] = None
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    message: str
    payload: Optional[Any] = None
    created_at: datetime


class WorkflowStatusResponse(BaseSchema):
    id: UUID
    story_id: UUID
    project_id: UUID
    organization_id: Optional[UUID] = None
    state: str
    last_event: Optional[str] = None
    retry_count: int
    max_retries: int
    last_error: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    cancel_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    version: int
    logs: List[WorkflowLogItem] = Field(default_factory=list)

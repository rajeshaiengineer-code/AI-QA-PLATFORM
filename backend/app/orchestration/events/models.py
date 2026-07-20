"""DomainEvent envelope."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.orchestration.events.enums import WorkflowEvent


class DomainEvent(BaseModel):
    """Standard event envelope for the workflow bus."""

    event_id: UUID = Field(default_factory=uuid4)
    event_type: WorkflowEvent
    occurred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    correlation_id: UUID
    causation_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    story_id: Optional[UUID] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

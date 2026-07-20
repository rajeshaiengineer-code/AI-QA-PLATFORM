"""Agent port — plugins perform stage work; they never mutate WorkflowState."""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.orchestration.events.enums import WorkflowEvent
from app.orchestration.state.enums import WorkflowState


class AgentContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    run_id: UUID
    organization_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    story_id: UUID
    workflow_state: WorkflowState
    input: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: UUID
    # Populated by WorkflowEngine so agents can use the same request session.
    session: Optional[Any] = None


class AgentResult(BaseModel):
    success: bool
    output: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
    emit_event: Optional[WorkflowEvent] = None
    retryable: bool = False


@runtime_checkable
class Agent(Protocol):
    name: str
    supported_events: List[WorkflowEvent]

    async def run(self, context: AgentContext) -> AgentResult: ...

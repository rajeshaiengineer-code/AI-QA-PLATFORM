"""ExecutionAgent — workflow plugin that runs the stub execution engine."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestration.agents.base import AgentContext, AgentResult
from app.orchestration.events.enums import WorkflowEvent
from app.schemas.execution import ExecutionRunRequest
from app.services.execution_engine import ExecutionEngineService

ServiceFactory = Callable[[AsyncSession], ExecutionEngineService]


class ExecutionAgent:
    """
    Agent registered for ``pull_request_created``.

    Runs the stub execution engine for the story (or an explicit artifact /
    job from ``context.input``), emits ``execution_started``, then returns
    ``execution_completed`` for the engine to apply.
    """

    name: str = "execution"
    supported_events: List[WorkflowEvent] = [
        WorkflowEvent.PULL_REQUEST_CREATED,
    ]

    def __init__(
        self,
        *,
        service_factory: Optional[ServiceFactory] = None,
    ) -> None:
        self._service_factory = service_factory or (
            lambda session: ExecutionEngineService(session)
        )

    async def run(self, context: AgentContext) -> AgentResult:
        if context.session is None:
            return AgentResult(
                success=False,
                error="Agent context is missing a database session",
                emit_event=WorkflowEvent.EXECUTION_FAILED_TO_START,
                retryable=False,
            )

        service = self._service_factory(context.session)
        payload: Dict[str, Any] = dict(context.input or {})

        try:
            # Do not pass workflow_run_id into the service — the agent owns
            # the two-step Started → Completed transition with the engine.
            request = self._build_request(context.story_id, payload)
            result = await service.run(request)

            from app.orchestration.events.models import DomainEvent
            from app.orchestration.runtime import get_workflow_engine

            engine = get_workflow_engine(context.session)
            await engine.on_event(
                DomainEvent(
                    event_type=WorkflowEvent.EXECUTION_STARTED,
                    correlation_id=context.run_id,
                    organization_id=context.organization_id,
                    project_id=context.project_id,
                    story_id=context.story_id,
                    payload={
                        "automation_job_id": str(result.job.id),
                        "runner": result.runner,
                    },
                )
            )
        except Exception as exc:
            return AgentResult(
                success=False,
                error=str(exc),
                emit_event=WorkflowEvent.EXECUTION_FAILED_TO_START,
                retryable=True,
                output={"error": str(exc)},
            )

        return AgentResult(
            success=True,
            emit_event=WorkflowEvent.EXECUTION_COMPLETED,
            output={
                "story_id": str(context.story_id),
                "automation_job_id": str(result.job.id),
                "status": result.job.status.value,
                "passed": result.job.passed,
                "failed": result.job.failed,
                "total": result.job.total,
                "runner": result.runner,
            },
            artifacts=[
                {
                    "type": "automation_job",
                    "id": str(result.job.id),
                    "status": result.job.status.value,
                }
            ],
        )

    def _build_request(
        self,
        story_id: UUID,
        payload: Dict[str, Any],
    ) -> ExecutionRunRequest:
        artifact_raw = payload.get("automation_artifact_id")
        job_raw = payload.get("automation_job_id")
        force_fail = payload.get("force_fail_test_case_ids")
        force_ids = (
            [UUID(str(x)) for x in force_fail] if force_fail else None
        )

        if job_raw:
            return ExecutionRunRequest(
                automation_job_id=UUID(str(job_raw)),
                force_fail_test_case_ids=force_ids,
                include_drafts=bool(payload.get("include_drafts", False)),
                name=payload.get("name"),
                config=payload.get("config"),
            )
        if artifact_raw:
            return ExecutionRunRequest(
                automation_artifact_id=UUID(str(artifact_raw)),
                force_fail_test_case_ids=force_ids,
                include_drafts=bool(payload.get("include_drafts", False)),
                name=payload.get("name"),
                config=payload.get("config"),
            )
        return ExecutionRunRequest(
            story_id=story_id,
            force_fail_test_case_ids=force_ids,
            include_drafts=bool(payload.get("include_drafts", False)),
            name=payload.get("name"),
            config=payload.get("config"),
        )

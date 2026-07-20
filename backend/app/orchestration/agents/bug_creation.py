"""BugCreationAgent — workflow plugin that files Jira bugs from analyses."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestration.agents.base import AgentContext, AgentResult
from app.orchestration.events.enums import WorkflowEvent
from app.schemas.bug import CreateJiraBugRequest
from app.services.bug_creation import BugCreationService

ServiceFactory = Callable[[AsyncSession], BugCreationService]


class BugCreationAgent:
    """
    Agent registered for ``failure_analyzed``.

    Creates Jira bugs for analyzed failed executions when ``jira_project_key``
    is provided in ``context.input``. Emits ``bug_created`` on success, or
    ``report_published`` when bug filing is skipped.
    """

    name: str = "bug_creation"
    supported_events: List[WorkflowEvent] = [
        WorkflowEvent.FAILURE_ANALYZED,
    ]

    def __init__(
        self,
        *,
        service_factory: Optional[ServiceFactory] = None,
    ) -> None:
        self._service_factory = service_factory or (
            lambda session: BugCreationService(session)
        )

    async def run(self, context: AgentContext) -> AgentResult:
        if context.session is None:
            return AgentResult(
                success=False,
                error="Agent context is missing a database session",
                emit_event=WorkflowEvent.WORKFLOW_FAILED,
                retryable=False,
            )

        payload: Dict[str, Any] = dict(context.input or {})
        project_key = payload.get("jira_project_key")
        if not project_key:
            return AgentResult(
                success=True,
                emit_event=WorkflowEvent.REPORT_PUBLISHED,
                output={
                    "created": 0,
                    "reason": "jira_project_key_not_provided",
                },
            )

        service = self._service_factory(context.session)
        execution_ids = self._resolve_execution_ids(payload)
        if not execution_ids:
            return AgentResult(
                success=True,
                emit_event=WorkflowEvent.REPORT_PUBLISHED,
                output={
                    "created": 0,
                    "reason": "no_execution_ids",
                },
            )

        bugs = []
        try:
            for execution_id in execution_ids:
                analysis_ids = payload.get("analysis_ids") or []
                analysis_id = None
                if analysis_ids and len(execution_ids) == 1:
                    analysis_id = UUID(str(analysis_ids[0]))
                request = CreateJiraBugRequest(
                    jira_project_key=str(project_key),
                    failure_analysis_id=analysis_id,
                    logs_url=payload.get("logs_url"),
                    execution_url=payload.get("execution_url"),
                    priority=payload.get("priority"),
                    labels=payload.get("labels"),
                )
                result = await service.create_jira_bug(execution_id, request)
                bugs.append(result)
        except Exception as exc:
            return AgentResult(
                success=False,
                error=str(exc),
                emit_event=WorkflowEvent.WORKFLOW_FAILED,
                retryable=True,
                output={"error": str(exc)},
            )

        return AgentResult(
            success=True,
            emit_event=WorkflowEvent.BUG_CREATED,
            output={
                "created": len(bugs),
                "bug_ids": [str(b.bug.id) for b in bugs],
                "jira_keys": [b.jira_key for b in bugs],
            },
            artifacts=[
                {
                    "type": "bug",
                    "id": str(b.bug.id),
                    "external_id": b.jira_key,
                }
                for b in bugs
            ],
        )

    def _resolve_execution_ids(self, payload: Dict[str, Any]) -> List[UUID]:
        raw = payload.get("execution_ids") or payload.get("execution_id")
        if not raw:
            return []
        if isinstance(raw, list):
            return [UUID(str(x)) for x in raw]
        return [UUID(str(raw))]

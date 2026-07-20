"""FailureAnalysisAgent — workflow plugin that analyzes failed executions."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ExecutionStatus
from app.orchestration.agents.base import AgentContext, AgentResult
from app.orchestration.events.enums import WorkflowEvent
from app.schemas.failure_analysis import FailureAnalyzeRequest
from app.services.failure_analyzer import FailureAnalyzerService

ServiceFactory = Callable[[AsyncSession], FailureAnalyzerService]


class FailureAnalysisAgent:
    """
    Agent registered for ``execution_completed``.

    Analyzes failed/error/blocked executions for the story's latest job
    (or an explicit execution_id from ``context.input``). Emits
    ``failure_analyzed`` when at least one analysis is produced; otherwise
    ``report_published`` so the happy path can complete.
    """

    name: str = "failure_analysis"
    supported_events: List[WorkflowEvent] = [
        WorkflowEvent.EXECUTION_COMPLETED,
    ]

    def __init__(
        self,
        *,
        service_factory: Optional[ServiceFactory] = None,
    ) -> None:
        self._service_factory = service_factory or (
            lambda session: FailureAnalyzerService(session)
        )

    async def run(self, context: AgentContext) -> AgentResult:
        if context.session is None:
            return AgentResult(
                success=False,
                error="Agent context is missing a database session",
                emit_event=WorkflowEvent.WORKFLOW_FAILED,
                retryable=False,
            )

        service = self._service_factory(context.session)
        payload: Dict[str, Any] = dict(context.input or {})
        evidence = FailureAnalyzeRequest(
            logs=payload.get("logs"),
            screenshot_url=payload.get("screenshot_url"),
            video_url=payload.get("video_url"),
            network_url=payload.get("network_url"),
            trace_url=payload.get("trace_url"),
            logical_model=payload.get("logical_model"),
        )

        try:
            execution_ids = await self._resolve_execution_ids(
                context.session,
                context.story_id,
                payload,
            )
            if not execution_ids:
                return AgentResult(
                    success=True,
                    emit_event=WorkflowEvent.REPORT_PUBLISHED,
                    output={
                        "analyzed": 0,
                        "reason": "no_failed_executions",
                    },
                )

            analyses = []
            for execution_id in execution_ids:
                analysis = await service.analyze_execution(execution_id, evidence)
                analyses.append(analysis)
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
            emit_event=WorkflowEvent.FAILURE_ANALYZED,
            output={
                "analyzed": len(analyses),
                "analysis_ids": [str(a.id) for a in analyses],
                "execution_ids": [str(a.execution_id) for a in analyses],
            },
            artifacts=[
                {"type": "failure_analysis", "id": str(a.id)} for a in analyses
            ],
        )

    async def _resolve_execution_ids(
        self,
        session: AsyncSession,
        story_id: UUID,
        payload: Dict[str, Any],
    ) -> List[UUID]:
        raw = payload.get("execution_id") or payload.get("execution_ids")
        if raw:
            if isinstance(raw, list):
                return [UUID(str(x)) for x in raw]
            return [UUID(str(raw))]

        from sqlalchemy import select

        from app.models.execution import Execution
        from app.models.test_case import TestCase

        # Latest failed executions for this story
        stmt = (
            select(Execution.id)
            .join(TestCase, TestCase.id == Execution.test_case_id)
            .where(
                TestCase.story_id == story_id,
                TestCase.is_deleted.is_(False),
                Execution.is_deleted.is_(False),
                Execution.status.in_(
                    [
                        ExecutionStatus.FAILED,
                        ExecutionStatus.ERROR,
                        ExecutionStatus.BLOCKED,
                    ]
                ),
            )
            .order_by(Execution.created_at.desc())
            .limit(20)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

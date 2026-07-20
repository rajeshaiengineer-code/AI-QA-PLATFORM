"""StoryAnalyzerAgent — workflow plugin that analyzes a story via AI."""

from typing import Callable, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestration.agents.base import AgentContext, AgentResult
from app.orchestration.events.enums import WorkflowEvent
from app.services.story_analyzer import StoryAnalyzerService

ServiceFactory = Callable[[AsyncSession], StoryAnalyzerService]


class StoryAnalyzerAgent:
    """
    Agent registered for story_imported / story_synced.

    Invokes StoryAnalyzerService and emits story_analyzed on success.
    Primary MVP path remains REST; this enables workflow advance when registered.
    """

    name: str = "story_analyzer"
    supported_events: List[WorkflowEvent] = [
        WorkflowEvent.STORY_IMPORTED,
        WorkflowEvent.STORY_SYNCED,
    ]

    def __init__(
        self,
        *,
        service_factory: Optional[ServiceFactory] = None,
    ) -> None:
        self._service_factory = service_factory or (
            lambda session: StoryAnalyzerService(session)
        )

    async def run(self, context: AgentContext) -> AgentResult:
        if context.session is None:
            return AgentResult(
                success=False,
                error="Agent context is missing a database session",
                emit_event=WorkflowEvent.ANALYSIS_FAILED,
                retryable=False,
            )

        service = self._service_factory(context.session)
        try:
            analysis = await service.analyze_story(context.story_id)
        except Exception as exc:
            return AgentResult(
                success=False,
                error=str(exc),
                emit_event=WorkflowEvent.ANALYSIS_FAILED,
                retryable=True,
                output={"error": str(exc)},
            )

        complexity = (
            analysis.complexity.value
            if hasattr(analysis.complexity, "value")
            else analysis.complexity
        )
        risk = (
            analysis.risk.value
            if hasattr(analysis.risk, "value")
            else analysis.risk
        )

        return AgentResult(
            success=True,
            emit_event=WorkflowEvent.STORY_ANALYZED,
            output={
                "analysis_id": str(analysis.id),
                "complexity": complexity,
                "risk": risk,
                "automation_candidate": analysis.automation_candidate,
                "summary": analysis.summary,
            },
            artifacts=[
                {
                    "type": "story_analysis",
                    "id": str(analysis.id),
                }
            ],
        )

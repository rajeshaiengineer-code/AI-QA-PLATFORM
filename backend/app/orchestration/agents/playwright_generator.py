"""PlaywrightGeneratorAgent — workflow plugin that generates Playwright automation."""

from typing import Callable, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestration.agents.base import AgentContext, AgentResult
from app.orchestration.events.enums import WorkflowEvent
from app.services.playwright_generator import PlaywrightGeneratorService

ServiceFactory = Callable[[AsyncSession], PlaywrightGeneratorService]


class PlaywrightGeneratorAgent:
    """
    Agent registered for bdd_generated.

    Invokes PlaywrightGeneratorService and emits automation_generated on success.
    Primary MVP path remains REST; this enables workflow advance when registered.
    """

    name: str = "playwright_generator"
    supported_events: List[WorkflowEvent] = [
        WorkflowEvent.BDD_GENERATED,
    ]

    def __init__(
        self,
        *,
        service_factory: Optional[ServiceFactory] = None,
    ) -> None:
        self._service_factory = service_factory or (
            lambda session: PlaywrightGeneratorService(session)
        )

    async def run(self, context: AgentContext) -> AgentResult:
        if context.session is None:
            return AgentResult(
                success=False,
                error="Agent context is missing a database session",
                emit_event=WorkflowEvent.AUTOMATION_FAILED,
                retryable=False,
            )

        service = self._service_factory(context.session)
        try:
            result = await service.generate_playwright(context.story_id)
        except Exception as exc:
            return AgentResult(
                success=False,
                error=str(exc),
                emit_event=WorkflowEvent.AUTOMATION_FAILED,
                retryable=True,
                output={"error": str(exc)},
            )

        return AgentResult(
            success=True,
            emit_event=WorkflowEvent.AUTOMATION_GENERATED,
            output={
                "story_id": str(result.story_id),
                "automation_artifact_id": str(result.artifact.id),
                "name": result.artifact.name,
                "file_count": result.file_count,
                "source_bdd_feature_count": result.source_bdd_feature_count,
                "source_test_case_count": result.source_test_case_count,
                "summary": result.summary,
                "provider": result.provider,
                "model": result.model,
            },
            artifacts=[
                {
                    "type": "automation_artifact",
                    "id": str(result.artifact.id),
                    "name": result.artifact.name,
                }
            ],
        )

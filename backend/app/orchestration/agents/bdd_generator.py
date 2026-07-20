"""BddGeneratorAgent — workflow plugin that generates Gherkin from approved cases."""

from typing import Callable, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestration.agents.base import AgentContext, AgentResult
from app.orchestration.events.enums import WorkflowEvent
from app.services.bdd_generator import BddGeneratorService

ServiceFactory = Callable[[AsyncSession], BddGeneratorService]


class BddGeneratorAgent:
    """
    Agent registered for story_approved.

    Invokes BddGeneratorService and emits bdd_generated on success.
    Primary MVP path remains REST; this enables workflow advance when registered.
    """

    name: str = "bdd_generator"
    supported_events: List[WorkflowEvent] = [
        WorkflowEvent.STORY_APPROVED,
    ]

    def __init__(
        self,
        *,
        service_factory: Optional[ServiceFactory] = None,
    ) -> None:
        self._service_factory = service_factory or (
            lambda session: BddGeneratorService(session)
        )

    async def run(self, context: AgentContext) -> AgentResult:
        if context.session is None:
            return AgentResult(
                success=False,
                error="Agent context is missing a database session",
                emit_event=WorkflowEvent.BDD_FAILED,
                retryable=False,
            )

        service = self._service_factory(context.session)
        try:
            result = await service.generate_bdd(context.story_id)
        except Exception as exc:
            return AgentResult(
                success=False,
                error=str(exc),
                emit_event=WorkflowEvent.BDD_FAILED,
                retryable=True,
                output={"error": str(exc)},
            )

        return AgentResult(
            success=True,
            emit_event=WorkflowEvent.BDD_GENERATED,
            output={
                "story_id": str(result.story_id),
                "bdd_feature_id": str(result.feature.id),
                "name": result.feature.name,
                "source_test_case_count": result.source_test_case_count,
                "summary": result.summary,
                "provider": result.provider,
                "model": result.model,
            },
            artifacts=[
                {
                    "type": "bdd_feature",
                    "id": str(result.feature.id),
                    "name": result.feature.name,
                }
            ],
        )

"""TestCaseGeneratorAgent — workflow plugin that generates test cases via AI."""

from typing import Callable, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestration.agents.base import AgentContext, AgentResult
from app.orchestration.events.enums import WorkflowEvent
from app.services.test_case_generator import TestCaseGeneratorService

ServiceFactory = Callable[[AsyncSession], TestCaseGeneratorService]


class TestCaseGeneratorAgent:
    """
    Agent registered for story_analyzed.

    Invokes TestCaseGeneratorService and emits test_cases_generated on success.
    Primary MVP path remains REST; this enables workflow advance when registered.
    """

    __test__ = False  # Prevent pytest from collecting this as a test class

    name: str = "test_case_generator"
    supported_events: List[WorkflowEvent] = [
        WorkflowEvent.STORY_ANALYZED,
    ]

    def __init__(
        self,
        *,
        service_factory: Optional[ServiceFactory] = None,
    ) -> None:
        self._service_factory = service_factory or (
            lambda session: TestCaseGeneratorService(session)
        )

    async def run(self, context: AgentContext) -> AgentResult:
        if context.session is None:
            return AgentResult(
                success=False,
                error="Agent context is missing a database session",
                emit_event=WorkflowEvent.TEST_GEN_FAILED,
                retryable=False,
            )

        service = self._service_factory(context.session)
        try:
            result = await service.generate_test_cases(context.story_id)
        except Exception as exc:
            return AgentResult(
                success=False,
                error=str(exc),
                emit_event=WorkflowEvent.TEST_GEN_FAILED,
                retryable=True,
                output={"error": str(exc)},
            )

        return AgentResult(
            success=True,
            emit_event=WorkflowEvent.TEST_CASES_GENERATED,
            output={
                "story_id": str(result.story_id),
                "count": result.count,
                "test_case_ids": [str(item.id) for item in result.items],
                "summary": result.summary,
                "provider": result.provider,
                "model": result.model,
            },
            artifacts=[
                {
                    "type": "test_case",
                    "id": str(item.id),
                    "category": item.category.value
                    if item.category is not None
                    and hasattr(item.category, "value")
                    else item.category,
                }
                for item in result.items
            ],
        )

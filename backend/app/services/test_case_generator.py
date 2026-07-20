"""
Test Case Generator Service

Runs AI test-case generation for a story, parses structured results, and persists them.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.ai import (
    AIError,
    ChatMessage,
    GenerateRequest,
    MessageRole,
)
from app.ai.base.provider import BaseAIProvider
from app.ai.factory import AIProviderFactory
from app.ai.models import ModelRegistry
from app.ai.prompts import PromptManager
from app.ai.runtime import ai_factory, model_registry, prompt_manager
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.acceptance_criteria import AcceptanceCriteria
from app.models.enums import Priority, TestCaseCategory, TestCaseSource, TestCaseStatus
from app.models.story import Story
from app.models.test_case import TestCase
from app.repositories.story import StoryRepository
from app.repositories.story_analysis import StoryAnalysisRepository
from app.repositories.test_case import TestCaseRepository
from app.schemas.base import PaginatedResponse
from app.schemas.test_case import (
    TestCaseGenerateResponse,
    TestCaseGenerateResult,
    TestCaseResponse,
)

PROMPT_NAME = "test_case_generate"
DEFAULT_LOGICAL_MODEL = "default"

ALL_CATEGORIES: Tuple[TestCaseCategory, ...] = tuple(TestCaseCategory)


class TestCaseGeneratorService:
    """Business orchestration for AI test case generation."""

    __test__ = False  # Prevent pytest from collecting this as a test class

    def __init__(
        self,
        session: AsyncSession,
        *,
        factory: Optional[AIProviderFactory] = None,
        models: Optional[ModelRegistry] = None,
        prompts: Optional[PromptManager] = None,
        provider: Optional[BaseAIProvider] = None,
        logical_model: str = DEFAULT_LOGICAL_MODEL,
    ) -> None:
        self.session = session
        self.story_repo = StoryRepository(session)
        self.analysis_repo = StoryAnalysisRepository(session)
        self.test_case_repo = TestCaseRepository(session)
        self._factory = factory or ai_factory
        self._models = models or model_registry
        self._prompts = prompts or prompt_manager
        self._provider_override = provider
        self._logical_model = logical_model

    async def generate_test_cases(
        self,
        story_id: UUID,
        *,
        logical_model: Optional[str] = None,
        categories: Optional[Sequence[TestCaseCategory]] = None,
    ) -> TestCaseGenerateResponse:
        """Generate test cases via the AI Framework and persist them."""
        story = await self.story_repo.get_by_id(story_id)
        if story is None:
            raise NotFoundException("Story", str(story_id))

        criteria = await self._list_acceptance_criteria(story_id)
        analysis = await self.analysis_repo.get_latest_for_story(story_id)
        category_list = list(categories) if categories else list(ALL_CATEGORIES)
        if not category_list:
            category_list = list(ALL_CATEGORIES)

        prompt = self._render_prompt(story, criteria, analysis, category_list)

        model_name = logical_model or self._logical_model
        provider, resolved_model = self._resolve_provider(model_name)

        try:
            response = await provider.generate(
                GenerateRequest(
                    model=resolved_model,
                    messages=[
                        ChatMessage(
                            role=MessageRole.SYSTEM,
                            content=(
                                "You are a senior QA engineer. "
                                "Respond with JSON only."
                            ),
                        ),
                        ChatMessage(role=MessageRole.USER, content=prompt),
                    ],
                    temperature=0.3,
                    max_tokens=8192,
                )
            )
        except AIError as exc:
            raise BadRequestException(
                message=f"AI test case generation failed: {exc.message}",
                details={"code": exc.code, **(exc.details or {})},
            ) from exc

        parsed = self._parse_generation_content(response.content)
        allowed = {c.value for c in category_list}
        drafts = [
            draft
            for draft in parsed.test_cases
            if draft.category.value in allowed
        ]
        if not drafts:
            raise BadRequestException(
                message="AI returned no usable test cases",
                details={"raw": response.content[:2000]},
            )

        start_index = await self.test_case_repo.max_order_index(story_id) + 1
        now = datetime.now(timezone.utc)
        entities: List[TestCase] = []
        for offset, draft in enumerate(drafts):
            ac_id = self._resolve_acceptance_criteria_id(
                draft.acceptance_criteria_index,
                criteria,
            )
            tags = list(draft.tags) if draft.tags else []
            if draft.category.value not in tags:
                tags = [draft.category.value] + tags

            entities.append(
                TestCase(
                    story_id=story.id,
                    acceptance_criteria_id=ac_id,
                    title=draft.title,
                    description=draft.description,
                    preconditions=draft.preconditions,
                    steps=[step.model_dump() for step in draft.steps],
                    expected_result=draft.expected_result,
                    priority=draft.priority,
                    is_automated=draft.is_automated,
                    order_index=start_index + offset,
                    category=draft.category.value,
                    source=TestCaseSource.AI.value,
                    status=TestCaseStatus.PENDING_REVIEW.value,
                    tags=tags,
                    provider=response.provider,
                    model=response.model,
                    created_at=now,
                    updated_at=now,
                )
            )

        created = await self.test_case_repo.add_many(entities)
        items = [TestCaseResponse.model_validate(entity) for entity in created]
        return TestCaseGenerateResponse(
            story_id=story.id,
            count=len(items),
            items=items,
            summary=parsed.summary,
            provider=response.provider,
            model=response.model,
            raw_response={
                "content": response.content,
                "finish_reason": response.finish_reason,
                "usage": response.usage.model_dump() if response.usage else None,
            },
        )

    async def list_test_cases(
        self,
        story_id: UUID,
        *,
        page: int = 1,
        page_size: int = 50,
        category: Optional[TestCaseCategory] = None,
        source: Optional[TestCaseSource] = None,
        status: Optional[TestCaseStatus] = None,
    ) -> PaginatedResponse[TestCaseResponse]:
        """List persisted test cases for a story."""
        story = await self.story_repo.get_by_id(story_id)
        if story is None:
            raise NotFoundException("Story", str(story_id))

        offset = (page - 1) * page_size
        rows, total = await self.test_case_repo.list_for_story(
            story_id,
            offset=offset,
            limit=page_size,
            category=category,
            source=source,
            status=status,
        )
        items = [TestCaseResponse.model_validate(row) for row in rows]
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    def _resolve_provider(self, logical_model: str) -> Tuple[BaseAIProvider, str]:
        if self._provider_override is not None:
            meta = self._provider_override.metadata()
            model = meta.default_model or logical_model
            return self._provider_override, model

        binding = self._models.resolve(logical_model)
        provider = self._factory.create(binding.provider)
        return provider, binding.model

    def _render_prompt(
        self,
        story: Story,
        criteria: List[AcceptanceCriteria],
        analysis: Any,
        categories: Sequence[TestCaseCategory],
    ) -> str:
        if criteria:
            ac_text = "\n".join(
                f"{idx}. {item.description}"
                for idx, item in enumerate(criteria, start=1)
            )
        else:
            ac_text = "(none provided)"

        if analysis is not None:
            analysis_context = (
                f"complexity={analysis.complexity}; risk={analysis.risk}; "
                f"automation_candidate={analysis.automation_candidate}; "
                f"summary={analysis.summary}; "
                f"suggested_tests={json.dumps(analysis.suggested_tests or [])}"
            )
        else:
            analysis_context = "(none — analyze the story first for better coverage)"

        return self._prompts.render(
            PROMPT_NAME,
            {
                "external_id": story.external_id or "(none)",
                "title": story.title,
                "story_type": story.story_type.value
                if hasattr(story.story_type, "value")
                else str(story.story_type),
                "priority": story.priority.value
                if hasattr(story.priority, "value")
                else str(story.priority),
                "status": story.status.value
                if hasattr(story.status, "value")
                else str(story.status),
                "story_points": story.story_points
                if story.story_points is not None
                else "(none)",
                "description": story.description or "(none)",
                "acceptance_criteria": ac_text,
                "analysis_context": analysis_context,
                "categories": ", ".join(c.value for c in categories),
            },
        )

    async def _list_acceptance_criteria(
        self,
        story_id: UUID,
    ) -> List[AcceptanceCriteria]:
        stmt = (
            select(AcceptanceCriteria)
            .options(
                noload(AcceptanceCriteria.story),
                noload(AcceptanceCriteria.test_cases),
            )
            .where(
                AcceptanceCriteria.story_id == story_id,
                AcceptanceCriteria.is_deleted.is_(False),
            )
            .order_by(AcceptanceCriteria.order_index.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def _resolve_acceptance_criteria_id(
        index: Optional[int],
        criteria: Sequence[AcceptanceCriteria],
    ) -> Optional[UUID]:
        if index is None or not criteria:
            return None
        # Prompt uses 1-based indexes
        zero_based = index - 1
        if zero_based < 0 or zero_based >= len(criteria):
            return None
        return criteria[zero_based].id

    @staticmethod
    def _parse_generation_content(content: str) -> TestCaseGenerateResult:
        """Parse LLM text into a validated TestCaseGenerateResult."""
        payload = TestCaseGeneratorService._extract_json(content)
        normalized = TestCaseGeneratorService._normalize_payload(payload)
        try:
            return TestCaseGenerateResult.model_validate(normalized)
        except Exception as exc:
            raise BadRequestException(
                message="AI returned an invalid test case payload",
                details={"error": str(exc), "raw": content[:2000]},
            ) from exc

    @staticmethod
    def _extract_json(content: str) -> Dict[str, Any]:
        text = (content or "").strip()
        if not text:
            raise BadRequestException(
                message="AI returned an empty test case response",
            )

        fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
        if fence:
            text = fence.group(1).strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end <= start:
                raise BadRequestException(
                    message="AI response was not valid JSON",
                    details={"raw": text[:2000]},
                )
            try:
                data = json.loads(text[start : end + 1])
            except json.JSONDecodeError as exc:
                raise BadRequestException(
                    message="AI response was not valid JSON",
                    details={"error": str(exc), "raw": text[:2000]},
                ) from exc

        if not isinstance(data, dict):
            raise BadRequestException(
                message="AI test case JSON must be an object",
            )
        return data

    @staticmethod
    def _normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(payload)
        raw_cases = data.get("test_cases") or data.get("cases") or []
        if isinstance(raw_cases, dict):
            raw_cases = [raw_cases]
        if isinstance(raw_cases, str):
            raw_cases = [{"title": raw_cases, "category": "positive"}]

        cases: List[Dict[str, Any]] = []
        for item in raw_cases:
            if isinstance(item, str):
                cases.append({"title": item, "category": "positive"})
                continue
            if not isinstance(item, dict):
                continue

            title = item.get("title") or item.get("name") or item.get("test")
            if not title:
                continue

            category = (
                item.get("category")
                or item.get("type")
                or item.get("test_type")
                or "positive"
            )
            category = str(category).strip().lower()
            if category not in {c.value for c in TestCaseCategory}:
                # Map common aliases
                aliases = {
                    "happy": "positive",
                    "happy_path": "positive",
                    "functional": "positive",
                    "edge": "boundary",
                    "edge_case": "boundary",
                    "a11y": "accessibility",
                    "perf": "performance",
                    "db": "database",
                }
                category = aliases.get(category, "positive")

            priority_raw = item.get("priority") or Priority.MEDIUM.value
            priority = str(priority_raw).strip().lower()
            if priority not in {p.value for p in Priority}:
                priority = Priority.MEDIUM.value

            steps_raw = item.get("steps") or []
            if isinstance(steps_raw, str):
                steps_raw = [{"action": steps_raw}]
            steps: List[Dict[str, Any]] = []
            for step in steps_raw:
                if isinstance(step, str):
                    steps.append({"action": step, "expected": None})
                elif isinstance(step, dict):
                    action = step.get("action") or step.get("step") or step.get("do")
                    if action:
                        steps.append(
                            {
                                "action": str(action),
                                "expected": step.get("expected")
                                or step.get("result"),
                            }
                        )

            tags_raw = item.get("tags") or []
            if isinstance(tags_raw, str):
                tags_raw = [tags_raw]
            tags = [str(t) for t in tags_raw if t]

            ac_index = item.get("acceptance_criteria_index")
            if ac_index is None:
                ac_index = item.get("ac_index")
            if ac_index is not None:
                try:
                    ac_index = int(ac_index)
                except (TypeError, ValueError):
                    ac_index = None

            cases.append(
                {
                    "title": str(title),
                    "description": item.get("description"),
                    "preconditions": item.get("preconditions")
                    or item.get("precondition"),
                    "steps": steps,
                    "expected_result": item.get("expected_result")
                    or item.get("expected"),
                    "priority": priority,
                    "category": category,
                    "tags": tags,
                    "is_automated": bool(item.get("is_automated", False)),
                    "acceptance_criteria_index": ac_index,
                }
            )

        data["test_cases"] = cases
        if not data.get("summary"):
            data["summary"] = f"Generated {len(cases)} test case(s)."
        return data

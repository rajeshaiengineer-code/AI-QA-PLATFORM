"""
Story Analyzer Service

Runs AI analysis on a story, parses structured results, and persists them.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
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
from app.models.story import Story
from app.models.story_analysis import StoryAnalysis
from app.repositories.story import StoryRepository
from app.repositories.story_analysis import StoryAnalysisRepository
from app.schemas.story_analysis import (
    StoryAnalysisResponse,
    StoryAnalysisResult,
)

PROMPT_NAME = "story_analyze"
DEFAULT_LOGICAL_MODEL = "default"


class StoryAnalyzerService:
    """Business orchestration for AI story analysis."""

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
        self._factory = factory or ai_factory
        self._models = models or model_registry
        self._prompts = prompts or prompt_manager
        self._provider_override = provider
        self._logical_model = logical_model

    async def analyze_story(
        self,
        story_id: UUID,
        *,
        logical_model: Optional[str] = None,
    ) -> StoryAnalysisResponse:
        """Analyze a story via the AI Framework and persist the result."""
        story = await self.story_repo.get_by_id(story_id)
        if story is None:
            raise NotFoundException("Story", str(story_id))

        criteria = await self._list_acceptance_criteria(story_id)
        prompt = self._render_prompt(story, criteria)

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
                                "You are a senior QA analyst. "
                                "Respond with JSON only."
                            ),
                        ),
                        ChatMessage(role=MessageRole.USER, content=prompt),
                    ],
                    temperature=0.2,
                    max_tokens=2048,
                )
            )
        except AIError as exc:
            raise BadRequestException(
                message=f"AI analysis failed: {exc.message}",
                details={"code": exc.code, **(exc.details or {})},
            ) from exc

        parsed = self._parse_analysis_content(response.content)
        now = datetime.now(timezone.utc)
        entity = StoryAnalysis(
            story_id=story.id,
            complexity=parsed.complexity.value,
            risk=parsed.risk.value,
            automation_candidate=parsed.automation_candidate,
            dependencies=list(parsed.dependencies),
            suggested_tests=[hint.model_dump() for hint in parsed.suggested_tests],
            summary=parsed.summary,
            notes=parsed.notes,
            provider=response.provider,
            model=response.model,
            raw_response={
                "content": response.content,
                "finish_reason": response.finish_reason,
                "usage": response.usage.model_dump() if response.usage else None,
            },
            created_at=now,
            updated_at=now,
        )
        created = await self.analysis_repo.add(entity)
        return StoryAnalysisResponse.model_validate(created)

    async def get_latest_analysis(self, story_id: UUID) -> StoryAnalysisResponse:
        """Return the latest persisted analysis for a story."""
        story = await self.story_repo.get_by_id(story_id)
        if story is None:
            raise NotFoundException("Story", str(story_id))

        analysis = await self.analysis_repo.get_latest_for_story(story_id)
        if analysis is None:
            raise NotFoundException("StoryAnalysis", f"story={story_id}")
        return StoryAnalysisResponse.model_validate(analysis)

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
    ) -> str:
        if criteria:
            ac_text = "\n".join(
                f"{idx}. {item.description}"
                for idx, item in enumerate(criteria, start=1)
            )
        else:
            ac_text = "(none provided)"

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
    def _parse_analysis_content(content: str) -> StoryAnalysisResult:
        """Parse LLM text into a validated StoryAnalysisResult."""
        payload = StoryAnalyzerService._extract_json(content)
        normalized = StoryAnalyzerService._normalize_payload(payload)
        try:
            return StoryAnalysisResult.model_validate(normalized)
        except Exception as exc:
            raise BadRequestException(
                message="AI returned an invalid analysis payload",
                details={"error": str(exc), "raw": content[:2000]},
            ) from exc

    @staticmethod
    def _extract_json(content: str) -> Dict[str, Any]:
        text = (content or "").strip()
        if not text:
            raise BadRequestException(
                message="AI returned an empty analysis response",
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
                message="AI analysis JSON must be an object",
            )
        return data

    @staticmethod
    def _normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(payload)

        deps = data.get("dependencies") or []
        if isinstance(deps, str):
            deps = [deps]
        data["dependencies"] = [str(item) for item in deps]

        tests_raw = data.get("suggested_tests") or []
        if isinstance(tests_raw, str):
            tests_raw = [tests_raw]
        tests: List[Dict[str, Any]] = []
        for item in tests_raw:
            if isinstance(item, str):
                tests.append({"title": item})
            elif isinstance(item, dict):
                title = item.get("title") or item.get("name") or item.get("test")
                if title:
                    tests.append(
                        {
                            "title": str(title),
                            "type": item.get("type"),
                            "rationale": item.get("rationale") or item.get("reason"),
                        }
                    )
        data["suggested_tests"] = tests

        if not data.get("summary"):
            data["summary"] = data.get("notes") or "Analysis completed."

        return data

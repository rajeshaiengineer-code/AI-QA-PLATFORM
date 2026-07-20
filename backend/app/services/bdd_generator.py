"""
BDD Generator Service

Generates Gherkin feature files from approved (or draft) test cases via AI.
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
from app.models.bdd_feature import BddFeature
from app.models.enums import TestCaseStatus
from app.models.story import Story
from app.models.test_case import TestCase
from app.repositories.bdd_feature import BddFeatureRepository
from app.repositories.story import StoryRepository
from app.repositories.test_case import TestCaseRepository
from app.schemas.base import PaginatedResponse
from app.schemas.bdd_feature import (
    BddFeatureResponse,
    BddGenerateResponse,
    BddGenerateResult,
    GherkinFeatureDraft,
)

PROMPT_NAME = "bdd_generate"
DEFAULT_LOGICAL_MODEL = "default"


class BddGeneratorService:
    """Business orchestration for AI BDD / Gherkin generation."""

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
        self.test_case_repo = TestCaseRepository(session)
        self.bdd_repo = BddFeatureRepository(session)
        self._factory = factory or ai_factory
        self._models = models or model_registry
        self._prompts = prompts or prompt_manager
        self._provider_override = provider
        self._logical_model = logical_model

    async def generate_bdd(
        self,
        story_id: UUID,
        *,
        logical_model: Optional[str] = None,
        include_drafts: bool = False,
    ) -> BddGenerateResponse:
        """Generate a Gherkin feature from eligible test cases and persist it."""
        story = await self.story_repo.get_by_id(story_id)
        if story is None:
            raise NotFoundException("Story", str(story_id))

        test_cases = await self._eligible_test_cases(story_id, include_drafts)
        if not test_cases:
            detail = (
                "No approved, draft, or pending_review test cases found"
                if include_drafts
                else "No approved test cases found (pass include_drafts=true to allow drafts)"
            )
            raise BadRequestException(
                message=detail,
                details={"story_id": str(story_id), "include_drafts": include_drafts},
            )

        criteria = await self._list_acceptance_criteria(story_id)
        prompt = self._render_prompt(story, criteria, test_cases)

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
                                "You are a senior QA engineer specializing in BDD. "
                                "Respond with JSON only."
                            ),
                        ),
                        ChatMessage(role=MessageRole.USER, content=prompt),
                    ],
                    temperature=0.3,
                    max_tokens=4096,
                )
            )
        except AIError as exc:
            raise BadRequestException(
                message=f"AI BDD generation failed: {exc.message}",
                details={"code": exc.code, **(exc.details or {})},
            ) from exc

        parsed = self._parse_generation_content(response.content)
        gherkin = (parsed.gherkin_content or "").strip() or self.render_gherkin(
            parsed.feature
        )
        if not gherkin.strip():
            raise BadRequestException(
                message="AI returned an empty Gherkin feature",
                details={"raw": response.content[:2000]},
            )

        now = datetime.now(timezone.utc)
        source_ids = [str(tc.id) for tc in test_cases]
        entity = BddFeature(
            story_id=story.id,
            name=parsed.feature.name,
            description=parsed.feature.description,
            gherkin_content=gherkin,
            tags=list(parsed.feature.tags) if parsed.feature.tags else [],
            scenarios=[s.model_dump() for s in parsed.feature.scenarios],
            source_test_case_ids=source_ids,
            include_drafts=include_drafts,
            provider=response.provider,
            model=response.model,
            summary=parsed.summary,
            raw_response={
                "content": response.content,
                "finish_reason": response.finish_reason,
                "usage": response.usage.model_dump() if response.usage else None,
            },
            created_at=now,
            updated_at=now,
        )
        created = await self.bdd_repo.add(entity)
        feature = BddFeatureResponse.model_validate(created)
        return BddGenerateResponse(
            story_id=story.id,
            feature=feature,
            summary=parsed.summary,
            provider=response.provider,
            model=response.model,
            source_test_case_count=len(test_cases),
            raw_response=feature.raw_response,
        )

    async def list_bdd_features(
        self,
        story_id: UUID,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[BddFeatureResponse]:
        """List persisted BDD features for a story."""
        story = await self.story_repo.get_by_id(story_id)
        if story is None:
            raise NotFoundException("Story", str(story_id))

        offset = (page - 1) * page_size
        rows, total = await self.bdd_repo.list_for_story(
            story_id,
            offset=offset,
            limit=page_size,
        )
        items = [BddFeatureResponse.model_validate(row) for row in rows]
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_bdd_feature(self, feature_id: UUID) -> BddFeatureResponse:
        """Return a single BDD feature by id."""
        entity = await self.bdd_repo.get_by_id(feature_id)
        if entity is None:
            raise NotFoundException("BddFeature", str(feature_id))
        return BddFeatureResponse.model_validate(entity)

    async def _eligible_test_cases(
        self,
        story_id: UUID,
        include_drafts: bool,
    ) -> Sequence[TestCase]:
        if include_drafts:
            statuses = (
                TestCaseStatus.APPROVED,
                TestCaseStatus.DRAFT,
                TestCaseStatus.PENDING_REVIEW,
            )
        else:
            statuses = (TestCaseStatus.APPROVED,)
        return await self.test_case_repo.list_for_story_by_statuses(
            story_id,
            statuses,
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
        test_cases: Sequence[TestCase],
    ) -> str:
        if criteria:
            ac_text = "\n".join(
                f"{idx}. {item.description}"
                for idx, item in enumerate(criteria, start=1)
            )
        else:
            ac_text = "(none provided)"

        cases_payload = []
        for tc in test_cases:
            cases_payload.append(
                {
                    "id": str(tc.id),
                    "title": tc.title,
                    "description": tc.description,
                    "preconditions": tc.preconditions,
                    "steps": tc.steps or [],
                    "expected_result": tc.expected_result,
                    "priority": tc.priority.value
                    if hasattr(tc.priority, "value")
                    else str(tc.priority),
                    "category": tc.category,
                    "tags": tc.tags or [],
                    "status": tc.status,
                }
            )

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
                "description": story.description or "(none)",
                "acceptance_criteria": ac_text,
                "test_cases_json": json.dumps(cases_payload, indent=2),
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
    def render_gherkin(feature: GherkinFeatureDraft) -> str:
        """Render structured feature JSON into a .feature file body."""
        lines: List[str] = []
        feature_tags = BddGeneratorService._format_tags(feature.tags)
        if feature_tags:
            lines.append(feature_tags)

        lines.append(f"Feature: {feature.name}")
        if feature.description:
            for desc_line in feature.description.strip().splitlines():
                lines.append(f"  {desc_line.strip()}")

        for scenario in feature.scenarios:
            lines.append("")
            scenario_tags = BddGeneratorService._format_tags(scenario.tags)
            if scenario_tags:
                lines.append(f"  {scenario_tags}")

            if scenario.type == "scenario_outline":
                lines.append(f"  Scenario Outline: {scenario.name}")
            else:
                lines.append(f"  Scenario: {scenario.name}")

            for step in scenario.steps:
                lines.append(f"    {step.keyword} {step.text}")

            if scenario.type == "scenario_outline" and scenario.examples is not None:
                lines.append("")
                example_tags = BddGeneratorService._format_tags(scenario.examples.tags)
                if example_tags:
                    lines.append(f"    {example_tags}")
                if scenario.examples.name:
                    lines.append(f"    Examples: {scenario.examples.name}")
                else:
                    lines.append("    Examples:")
                header = " | ".join(scenario.examples.headers)
                lines.append(f"      | {header} |")
                for row in scenario.examples.rows:
                    cells = " | ".join(str(c) for c in row)
                    lines.append(f"      | {cells} |")

        return "\n".join(lines).rstrip() + "\n"

    @staticmethod
    def _format_tags(tags: Optional[Sequence[str]]) -> str:
        if not tags:
            return ""
        normalized: List[str] = []
        for tag in tags:
            text = str(tag).strip()
            if not text:
                continue
            if not text.startswith("@"):
                text = f"@{text}"
            normalized.append(text)
        return " ".join(normalized)

    @staticmethod
    def _parse_generation_content(content: str) -> BddGenerateResult:
        payload = BddGeneratorService._extract_json(content)
        normalized = BddGeneratorService._normalize_payload(payload)
        try:
            return BddGenerateResult.model_validate(normalized)
        except Exception as exc:
            raise BadRequestException(
                message="AI returned an invalid BDD payload",
                details={"error": str(exc), "raw": content[:2000]},
            ) from exc

    @staticmethod
    def _extract_json(content: str) -> Dict[str, Any]:
        text = (content or "").strip()
        if not text:
            raise BadRequestException(
                message="AI returned an empty BDD response",
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
                message="AI BDD JSON must be an object",
            )
        return data

    @staticmethod
    def _normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(payload)
        feature_raw = data.get("feature") or data
        if isinstance(feature_raw, str):
            # Treat as name-only stub — invalid later
            feature_raw = {"name": feature_raw, "scenarios": []}
        if not isinstance(feature_raw, dict):
            raise BadRequestException(message="AI BDD feature must be an object")

        name = (
            feature_raw.get("name")
            or feature_raw.get("title")
            or feature_raw.get("feature")
        )
        if not name:
            raise BadRequestException(message="AI BDD feature is missing a name")

        tags_raw = feature_raw.get("tags") or []
        if isinstance(tags_raw, str):
            tags_raw = [tags_raw]
        tags = [str(t) for t in tags_raw if t]

        scenarios_raw = (
            feature_raw.get("scenarios")
            or feature_raw.get("scenario")
            or []
        )
        if isinstance(scenarios_raw, dict):
            scenarios_raw = [scenarios_raw]

        scenarios: List[Dict[str, Any]] = []
        for item in scenarios_raw:
            if not isinstance(item, dict):
                continue
            scenario_name = item.get("name") or item.get("title")
            if not scenario_name:
                continue

            stype = str(
                item.get("type") or item.get("scenario_type") or "scenario"
            ).strip().lower()
            if stype in {"outline", "scenario outline", "scenariooutline"}:
                stype = "scenario_outline"
            if stype not in {"scenario", "scenario_outline"}:
                stype = "scenario"

            scenario_tags = item.get("tags") or []
            if isinstance(scenario_tags, str):
                scenario_tags = [scenario_tags]

            steps_raw = item.get("steps") or []
            if isinstance(steps_raw, str):
                steps_raw = [{"keyword": "Given", "text": steps_raw}]
            steps: List[Dict[str, Any]] = []
            for step in steps_raw:
                if isinstance(step, str):
                    steps.append({"keyword": "Given", "text": step})
                elif isinstance(step, dict):
                    keyword = (
                        step.get("keyword")
                        or step.get("type")
                        or "Given"
                    )
                    text = step.get("text") or step.get("step") or step.get("action")
                    if text:
                        steps.append(
                            {"keyword": str(keyword), "text": str(text)}
                        )

            examples = None
            examples_raw = item.get("examples") or item.get("example")
            if examples_raw and isinstance(examples_raw, dict):
                headers = examples_raw.get("headers") or examples_raw.get("columns") or []
                if isinstance(headers, str):
                    headers = [headers]
                rows = examples_raw.get("rows") or examples_raw.get("data") or []
                if rows and isinstance(rows[0], dict):
                    # Convert list of dicts using headers order
                    if not headers:
                        headers = list(rows[0].keys())
                    converted = []
                    for row in rows:
                        if isinstance(row, dict):
                            converted.append(
                                [str(row.get(h, "")) for h in headers]
                            )
                        elif isinstance(row, (list, tuple)):
                            converted.append([str(c) for c in row])
                    rows = converted
                else:
                    rows = [
                        [str(c) for c in row]
                        for row in rows
                        if isinstance(row, (list, tuple))
                    ]
                ex_tags = examples_raw.get("tags") or []
                if isinstance(ex_tags, str):
                    ex_tags = [ex_tags]
                if headers:
                    examples = {
                        "name": examples_raw.get("name"),
                        "tags": [str(t) for t in ex_tags if t],
                        "headers": [str(h) for h in headers],
                        "rows": rows,
                    }

            if stype == "scenario_outline" and examples is None:
                # Downgrade if AI forgot examples
                stype = "scenario"

            scenarios.append(
                {
                    "type": stype,
                    "name": str(scenario_name),
                    "tags": [str(t) for t in scenario_tags if t],
                    "steps": steps,
                    "examples": examples,
                }
            )

        data["feature"] = {
            "name": str(name),
            "description": feature_raw.get("description"),
            "tags": tags,
            "scenarios": scenarios,
        }
        if not data.get("summary"):
            data["summary"] = f"Generated BDD feature with {len(scenarios)} scenario(s)."
        if "gherkin_content" not in data and feature_raw.get("gherkin_content"):
            data["gherkin_content"] = feature_raw.get("gherkin_content")
        return data

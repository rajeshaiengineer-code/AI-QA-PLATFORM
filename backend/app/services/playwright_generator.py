"""
Playwright Generator Service

Generates Playwright TypeScript automation from BDD features and/or test cases via AI.
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
from app.models.automation_artifact import AutomationArtifact
from app.models.bdd_feature import BddFeature
from app.models.enums import TestCaseStatus
from app.models.story import Story
from app.models.test_case import TestCase
from app.repositories.automation_artifact import AutomationArtifactRepository
from app.repositories.bdd_feature import BddFeatureRepository
from app.repositories.story import StoryRepository
from app.repositories.test_case import TestCaseRepository
from app.schemas.automation_artifact import (
    AutomationArtifactResponse,
    PlaywrightGenerateResponse,
    PlaywrightGenerateResult,
    PlaywrightSuiteDraft,
)
from app.schemas.base import PaginatedResponse

PROMPT_NAME = "playwright_generate"
DEFAULT_LOGICAL_MODEL = "default"

_KIND_TO_FIELD = {
    "page_object": "page_objects",
    "locator": "locators",
    "fixture": "fixtures",
    "utility": "utilities",
    "assertion": "assertions",
    "hook": "hooks",
    "spec": "specs",
}


class PlaywrightGeneratorService:
    """Business orchestration for AI Playwright TypeScript generation."""

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
        self.artifact_repo = AutomationArtifactRepository(session)
        self._factory = factory or ai_factory
        self._models = models or model_registry
        self._prompts = prompts or prompt_manager
        self._provider_override = provider
        self._logical_model = logical_model

    async def generate_playwright(
        self,
        story_id: UUID,
        *,
        logical_model: Optional[str] = None,
        use_bdd: bool = True,
        use_test_cases: bool = True,
        include_drafts: bool = False,
    ) -> PlaywrightGenerateResponse:
        """Generate Playwright automation from BDD and/or test cases and persist it."""
        if not use_bdd and not use_test_cases:
            raise BadRequestException(
                message="at least one of use_bdd or use_test_cases must be true",
            )

        story = await self.story_repo.get_by_id(story_id)
        if story is None:
            raise NotFoundException("Story", str(story_id))

        bdd_features: Sequence[BddFeature] = []
        if use_bdd:
            bdd_features, _ = await self.bdd_repo.list_for_story(
                story_id,
                offset=0,
                limit=100,
            )

        test_cases: Sequence[TestCase] = []
        if use_test_cases:
            test_cases = await self._eligible_test_cases(story_id, include_drafts)

        if not bdd_features and not test_cases:
            details: Dict[str, Any] = {
                "story_id": str(story_id),
                "use_bdd": use_bdd,
                "use_test_cases": use_test_cases,
                "include_drafts": include_drafts,
            }
            if use_bdd and use_test_cases:
                message = (
                    "No BDD features or eligible test cases found "
                    "(generate BDD first and/or approve test cases)"
                )
            elif use_bdd:
                message = "No BDD features found for this story"
            else:
                message = (
                    "No approved test cases found "
                    "(pass include_drafts=true to allow drafts)"
                    if not include_drafts
                    else "No approved, draft, or pending_review test cases found"
                )
            raise BadRequestException(message=message, details=details)

        criteria = await self._list_acceptance_criteria(story_id)
        prompt = self._render_prompt(story, criteria, bdd_features, test_cases)

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
                                "You are a senior QA automation engineer specializing "
                                "in Playwright and TypeScript. Respond with JSON only."
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
                message=f"AI Playwright generation failed: {exc.message}",
                details={"code": exc.code, **(exc.details or {})},
            ) from exc

        parsed = self._parse_generation_content(response.content)
        suite = parsed.suite
        file_count = self._count_files(suite)

        now = datetime.now(timezone.utc)
        entity = AutomationArtifact(
            story_id=story.id,
            name=suite.name,
            description=suite.description,
            language=suite.language or "typescript",
            framework=suite.framework or "playwright",
            page_objects=[f.model_dump() for f in suite.page_objects],
            locators=[f.model_dump() for f in suite.locators],
            fixtures=[f.model_dump() for f in suite.fixtures],
            utilities=[f.model_dump() for f in suite.utilities],
            assertions=[f.model_dump() for f in suite.assertions],
            hooks=[f.model_dump() for f in suite.hooks],
            specs=[f.model_dump() for f in suite.specs],
            source_bdd_feature_ids=[str(f.id) for f in bdd_features],
            source_test_case_ids=[str(tc.id) for tc in test_cases],
            use_bdd=use_bdd,
            use_test_cases=use_test_cases,
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
        created = await self.artifact_repo.add(entity)
        artifact = AutomationArtifactResponse.model_validate(created)
        return PlaywrightGenerateResponse(
            story_id=story.id,
            artifact=artifact,
            summary=parsed.summary,
            provider=response.provider,
            model=response.model,
            source_bdd_feature_count=len(bdd_features),
            source_test_case_count=len(test_cases),
            file_count=file_count,
            raw_response=artifact.raw_response,
        )

    async def list_artifacts(
        self,
        story_id: UUID,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[AutomationArtifactResponse]:
        """List persisted Playwright artifacts for a story."""
        story = await self.story_repo.get_by_id(story_id)
        if story is None:
            raise NotFoundException("Story", str(story_id))

        offset = (page - 1) * page_size
        rows, total = await self.artifact_repo.list_for_story(
            story_id,
            offset=offset,
            limit=page_size,
        )
        items = [AutomationArtifactResponse.model_validate(row) for row in rows]
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_artifact(self, artifact_id: UUID) -> AutomationArtifactResponse:
        """Return a single automation artifact by id."""
        entity = await self.artifact_repo.get_by_id(artifact_id)
        if entity is None:
            raise NotFoundException("AutomationArtifact", str(artifact_id))
        return AutomationArtifactResponse.model_validate(entity)

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
        bdd_features: Sequence[BddFeature],
        test_cases: Sequence[TestCase],
    ) -> str:
        if criteria:
            ac_text = "\n".join(
                f"{idx}. {item.description}"
                for idx, item in enumerate(criteria, start=1)
            )
        else:
            ac_text = "(none provided)"

        bdd_payload = []
        for feat in bdd_features:
            bdd_payload.append(
                {
                    "id": str(feat.id),
                    "name": feat.name,
                    "description": feat.description,
                    "tags": feat.tags or [],
                    "scenarios": feat.scenarios or [],
                    "gherkin_content": feat.gherkin_content,
                }
            )

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
                "bdd_features_json": json.dumps(bdd_payload, indent=2),
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
    def _count_files(suite: PlaywrightSuiteDraft) -> int:
        return (
            len(suite.page_objects)
            + len(suite.locators)
            + len(suite.fixtures)
            + len(suite.utilities)
            + len(suite.assertions)
            + len(suite.hooks)
            + len(suite.specs)
        )

    @staticmethod
    def _parse_generation_content(content: str) -> PlaywrightGenerateResult:
        payload = PlaywrightGeneratorService._extract_json(content)
        normalized = PlaywrightGeneratorService._normalize_payload(payload)
        try:
            return PlaywrightGenerateResult.model_validate(normalized)
        except Exception as exc:
            raise BadRequestException(
                message="AI returned an invalid Playwright payload",
                details={"error": str(exc), "raw": content[:2000]},
            ) from exc

    @staticmethod
    def _extract_json(content: str) -> Dict[str, Any]:
        text = (content or "").strip()
        if not text:
            raise BadRequestException(
                message="AI returned an empty Playwright response",
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
                message="AI Playwright JSON must be an object",
            )
        return data

    @staticmethod
    def _normalize_file(item: Any) -> Optional[Dict[str, Any]]:
        if isinstance(item, str):
            return None
        if not isinstance(item, dict):
            return None
        path = item.get("path") or item.get("file") or item.get("filename")
        content = item.get("content") or item.get("code") or item.get("source")
        if not path or not content:
            return None
        result: Dict[str, Any] = {
            "path": str(path).strip().lstrip("/"),
            "content": str(content),
        }
        if item.get("description"):
            result["description"] = str(item["description"])
        return result

    @staticmethod
    def _normalize_file_list(raw: Any) -> List[Dict[str, Any]]:
        if raw is None:
            return []
        if isinstance(raw, dict):
            raw = [raw]
        if not isinstance(raw, list):
            return []
        files: List[Dict[str, Any]] = []
        for item in raw:
            normalized = PlaywrightGeneratorService._normalize_file(item)
            if normalized:
                files.append(normalized)
        return files

    @staticmethod
    def _normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(payload)
        suite_raw = data.get("suite") or data.get("automation") or data
        if isinstance(suite_raw, str):
            suite_raw = {"name": suite_raw}
        if not isinstance(suite_raw, dict):
            raise BadRequestException(message="AI Playwright suite must be an object")

        name = (
            suite_raw.get("name")
            or suite_raw.get("title")
            or suite_raw.get("package")
            or "playwright-suite"
        )

        groups: Dict[str, List[Dict[str, Any]]] = {
            "page_objects": PlaywrightGeneratorService._normalize_file_list(
                suite_raw.get("page_objects") or suite_raw.get("pages")
            ),
            "locators": PlaywrightGeneratorService._normalize_file_list(
                suite_raw.get("locators") or suite_raw.get("selectors")
            ),
            "fixtures": PlaywrightGeneratorService._normalize_file_list(
                suite_raw.get("fixtures")
            ),
            "utilities": PlaywrightGeneratorService._normalize_file_list(
                suite_raw.get("utilities")
                or suite_raw.get("utils")
                or suite_raw.get("helpers")
            ),
            "assertions": PlaywrightGeneratorService._normalize_file_list(
                suite_raw.get("assertions") or suite_raw.get("expects")
            ),
            "hooks": PlaywrightGeneratorService._normalize_file_list(
                suite_raw.get("hooks")
            ),
            "specs": PlaywrightGeneratorService._normalize_file_list(
                suite_raw.get("specs")
                or suite_raw.get("tests")
                or suite_raw.get("test_files")
            ),
        }

        # Flat "files" array with kind hints
        flat = suite_raw.get("files") or data.get("files")
        if isinstance(flat, list):
            for item in flat:
                if not isinstance(item, dict):
                    continue
                kind = str(
                    item.get("kind") or item.get("type") or item.get("artifact_type") or ""
                ).strip().lower()
                field = _KIND_TO_FIELD.get(kind)
                if field is None:
                    # Infer from path
                    path = str(item.get("path") or "").lower()
                    if "page" in path:
                        field = "page_objects"
                    elif "locator" in path or "selector" in path:
                        field = "locators"
                    elif "fixture" in path:
                        field = "fixtures"
                    elif "assert" in path:
                        field = "assertions"
                    elif "hook" in path or "setup" in path:
                        field = "hooks"
                    elif "spec" in path or "test" in path:
                        field = "specs"
                    else:
                        field = "utilities"
                normalized = PlaywrightGeneratorService._normalize_file(item)
                if normalized:
                    groups[field].append(normalized)

        data["suite"] = {
            "name": str(name),
            "description": suite_raw.get("description"),
            "language": suite_raw.get("language") or "typescript",
            "framework": suite_raw.get("framework") or "playwright",
            **groups,
        }
        if not data.get("summary"):
            total = sum(len(v) for v in groups.values())
            data["summary"] = f"Generated Playwright suite with {total} file(s)."
        return data

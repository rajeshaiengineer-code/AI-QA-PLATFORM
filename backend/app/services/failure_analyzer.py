"""
Failure Analyzer Service

Runs AI analysis on a failed Execution, parses structured results, and persists them.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple
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
from app.models.enums import ExecutionStatus, FailureCategory
from app.models.execution import Execution
from app.models.failure_analysis import FailureAnalysis
from app.models.test_case import TestCase
from app.repositories.execution import ExecutionRepository
from app.repositories.failure_analysis import FailureAnalysisRepository
from app.schemas.failure_analysis import (
    FailureAnalysisResponse,
    FailureAnalysisResult,
    FailureAnalyzeRequest,
)

PROMPT_NAME = "failure_analyze"
DEFAULT_LOGICAL_MODEL = "default"

_ANALYZABLE_STATUSES = {
    ExecutionStatus.FAILED,
    ExecutionStatus.ERROR,
    ExecutionStatus.BLOCKED,
}


class FailureAnalyzerService:
    """Business orchestration for AI failure analysis."""

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
        self.execution_repo = ExecutionRepository(session)
        self.analysis_repo = FailureAnalysisRepository(session)
        self._factory = factory or ai_factory
        self._models = models or model_registry
        self._prompts = prompts or prompt_manager
        self._provider_override = provider
        self._logical_model = logical_model

    async def analyze_execution(
        self,
        execution_id: UUID,
        request: Optional[FailureAnalyzeRequest] = None,
    ) -> FailureAnalysisResponse:
        """Analyze a failed execution via the AI Framework and persist the result."""
        request = request or FailureAnalyzeRequest()
        execution = await self.execution_repo.get_by_id(execution_id)
        if execution is None:
            raise NotFoundException("Execution", str(execution_id))

        status = (
            execution.status
            if isinstance(execution.status, ExecutionStatus)
            else ExecutionStatus(str(execution.status))
        )
        if status not in _ANALYZABLE_STATUSES:
            raise BadRequestException(
                message=(
                    f"Execution status '{status.value}' is not analyzable — "
                    "expected failed, error, or blocked"
                ),
                details={"execution_id": str(execution_id), "status": status.value},
            )

        test_case = await self._get_test_case(execution.test_case_id)
        prompt = self._render_prompt(execution, test_case, request)

        model_name = request.logical_model or self._logical_model
        provider, resolved_model = self._resolve_provider(model_name)

        try:
            response = await provider.generate(
                GenerateRequest(
                    model=resolved_model,
                    messages=[
                        ChatMessage(
                            role=MessageRole.SYSTEM,
                            content=(
                                "You are a senior QA failure analyst. "
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
                message=f"AI failure analysis failed: {exc.message}",
                details={"code": exc.code, **(exc.details or {})},
            ) from exc

        parsed = self._parse_analysis_content(response.content)
        now = datetime.now(timezone.utc)
        entity = FailureAnalysis(
            execution_id=execution.id,
            category=parsed.category.value,
            is_flaky=parsed.is_flaky,
            is_product_bug=parsed.is_product_bug,
            summary=parsed.summary,
            root_cause=parsed.root_cause,
            suggested_fix=parsed.suggested_fix,
            confidence=parsed.confidence,
            notes=parsed.notes,
            logs=request.logs,
            screenshot_url=request.screenshot_url,
            video_url=request.video_url,
            network_url=request.network_url,
            trace_url=request.trace_url,
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
        return FailureAnalysisResponse.model_validate(created)

    async def get_latest_analysis(
        self,
        execution_id: UUID,
    ) -> FailureAnalysisResponse:
        """Return the latest persisted analysis for an execution."""
        execution = await self.execution_repo.get_by_id(execution_id)
        if execution is None:
            raise NotFoundException("Execution", str(execution_id))

        analysis = await self.analysis_repo.get_latest_for_execution(execution_id)
        if analysis is None:
            raise NotFoundException("FailureAnalysis", f"execution={execution_id}")
        return FailureAnalysisResponse.model_validate(analysis)

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
        execution: Execution,
        test_case: Optional[TestCase],
        request: FailureAnalyzeRequest,
    ) -> str:
        status = (
            execution.status.value
            if hasattr(execution.status, "value")
            else str(execution.status)
        )
        return self._prompts.render(
            PROMPT_NAME,
            {
                "execution_id": str(execution.id),
                "status": status,
                "test_case_title": (test_case.title if test_case else "(unknown)"),
                "test_case_steps": (
                    json.dumps(test_case.steps)
                    if test_case and test_case.steps
                    else "(none)"
                ),
                "expected_result": (
                    test_case.expected_result
                    if test_case and test_case.expected_result
                    else "(none)"
                ),
                "error_message": execution.error_message or "(none)",
                "stack_trace": execution.stack_trace or "(none)",
                "evidence_url": execution.evidence_url or "(none)",
                "retry_count": execution.retry_count,
                "logs": request.logs or "(none)",
                "screenshot_url": request.screenshot_url or "(none)",
                "video_url": request.video_url or "(none)",
                "network_url": request.network_url or "(none)",
                "trace_url": request.trace_url or "(none)",
            },
        )

    async def _get_test_case(self, test_case_id: UUID) -> Optional[TestCase]:
        stmt = (
            select(TestCase)
            .options(
                noload(TestCase.story),
                noload(TestCase.acceptance_criteria),
                noload(TestCase.executions),
                noload(TestCase.bugs),
                noload(TestCase.versions),
            )
            .where(
                TestCase.id == test_case_id,
                TestCase.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _parse_analysis_content(content: str) -> FailureAnalysisResult:
        payload = FailureAnalyzerService._extract_json(content)
        normalized = FailureAnalyzerService._normalize_payload(payload)
        try:
            return FailureAnalysisResult.model_validate(normalized)
        except Exception as exc:
            raise BadRequestException(
                message="AI returned an invalid failure analysis payload",
                details={"error": str(exc), "raw": content[:2000]},
            ) from exc

    @staticmethod
    def _extract_json(content: str) -> Dict[str, Any]:
        text = (content or "").strip()
        if not text:
            raise BadRequestException(
                message="AI returned an empty failure analysis response",
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
                message="AI failure analysis JSON must be an object",
            )
        return data

    @staticmethod
    def _normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(payload)

        category = data.get("category") or data.get("classification") or "unknown"
        if isinstance(category, str):
            category = category.strip().lower().replace(" ", "_").replace("-", "_")
        data["category"] = category
        if category not in {c.value for c in FailureCategory}:
            data["category"] = FailureCategory.UNKNOWN.value

        if "is_flaky" not in data:
            data["is_flaky"] = category == FailureCategory.FLAKY.value
        if "is_product_bug" not in data:
            data["is_product_bug"] = category == FailureCategory.PRODUCT_BUG.value

        if not data.get("summary"):
            data["summary"] = data.get("root_cause") or "Failure analysis completed."
        if not data.get("root_cause"):
            data["root_cause"] = data.get("summary") or "Unknown root cause."
        if not data.get("suggested_fix"):
            data["suggested_fix"] = (
                data.get("fix")
                or data.get("recommendation")
                or "Investigate failure evidence and re-run."
            )

        confidence = data.get("confidence")
        if confidence is not None:
            try:
                conf = float(confidence)
                if conf > 1.0:
                    conf = conf / 100.0
                data["confidence"] = max(0.0, min(1.0, conf))
            except (TypeError, ValueError):
                data["confidence"] = None

        return data

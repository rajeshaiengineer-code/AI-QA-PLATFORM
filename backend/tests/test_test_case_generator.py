"""
Unit / API tests for AI Test Case Generator.

AI provider HTTP is mocked — no live API keys required.
"""

import json
from typing import Any, Optional
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.base.provider import BaseAIProvider
from app.ai.base.types import (
    AIHealth,
    AIProviderMetadata,
    GenerateRequest,
    GenerateResponse,
    HealthStatus,
)
from app.api.v1.endpoints import stories as stories_ep
from app.main import app
from app.models.acceptance_criteria import AcceptanceCriteria
from app.models.project import Project
from app.models.story import Story
from app.orchestration.agents.base import AgentContext
from app.orchestration.agents.test_case_generator import TestCaseGeneratorAgent
from app.orchestration.events.enums import WorkflowEvent
from app.orchestration.runtime import get_agent_registry, register_builtin_agents
from app.orchestration.state.enums import WorkflowState
from app.services.test_case_generator import TestCaseGeneratorService


STORIES_URL = "/api/v1/stories"

MOCK_GENERATION = {
    "summary": "Coverage across happy path, negatives, and API checks.",
    "test_cases": [
        {
            "title": "Reset password with valid token",
            "description": "Happy path",
            "preconditions": "Valid reset token exists",
            "steps": [
                {"action": "Open reset link", "expected": "Form loads"},
                {"action": "Submit new password", "expected": "Success"},
            ],
            "expected_result": "Password updated",
            "priority": "high",
            "category": "positive",
            "tags": ["auth"],
            "is_automated": True,
            "acceptance_criteria_index": 1,
        },
        {
            "title": "Reject expired reset token",
            "steps": [{"action": "Open expired link", "expected": "Error shown"}],
            "expected_result": "User cannot reset",
            "priority": "high",
            "category": "negative",
            "tags": [],
            "is_automated": False,
        },
        {
            "title": "Password min length boundary",
            "category": "boundary",
            "priority": "medium",
            "steps": [{"action": "Submit 7-char password"}],
            "expected_result": "Validation error",
        },
        {
            "title": "POST /password-reset returns 202",
            "category": "api",
            "priority": "medium",
            "steps": [{"action": "Call API with valid payload"}],
        },
        {
            "title": "Token not guessable",
            "category": "security",
            "priority": "critical",
            "steps": [{"action": "Inspect token entropy"}],
        },
        {
            "title": "Reset token persisted hashed",
            "category": "database",
            "priority": "high",
            "steps": [{"action": "Inspect DB row"}],
        },
        {
            "title": "Reset form keyboard accessible",
            "category": "accessibility",
            "priority": "medium",
            "steps": [{"action": "Tab through form"}],
        },
        {
            "title": "Reset email arrives within SLA",
            "category": "performance",
            "priority": "low",
            "steps": [{"action": "Measure email latency"}],
        },
    ],
}


class MockAIProvider(BaseAIProvider):
    """Test double that returns fixed JSON generation content."""

    def __init__(
        self,
        content: Optional[str] = None,
        *,
        fail: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key="test-key", **kwargs)
        self._content = content or json.dumps(MOCK_GENERATION)
        self._fail = fail
        self.calls = 0

    def metadata(self) -> AIProviderMetadata:
        return AIProviderMetadata(
            name="mock-ai",
            display_name="Mock AI",
            version="1.0.0",
            default_model="mock-1",
            capabilities=["generate"],
        )

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        self.calls += 1
        if self._fail:
            from app.ai import AIGenerationError

            raise AIGenerationError("simulated provider failure")
        return GenerateResponse(
            content=self._content,
            model=request.model,
            provider="mock-ai",
            finish_reason="stop",
        )

    async def health_check(self) -> AIHealth:
        return AIHealth(status=HealthStatus.HEALTHY, provider="mock-ai")


def _story_payload(project_id, **overrides):
    data = {
        "project_id": str(project_id),
        "title": "User can reset password",
        "description": "As a user I want to reset my password via email.",
        "external_id": "TST-TCG-1",
    }
    data.update(overrides)
    return data


def _override_generator(mock: MockAIProvider, db_session: AsyncSession) -> None:
    def _dep() -> TestCaseGeneratorService:
        return TestCaseGeneratorService(db_session, provider=mock)

    app.dependency_overrides[stories_ep.get_test_case_generator_service] = _dep


@pytest.mark.asyncio
async def test_generate_test_cases_persists(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_project: Project,
):
    created = await client.post(STORIES_URL, json=_story_payload(seed_project.id))
    assert created.status_code == 201
    story_id = created.json()["id"]

    mock = MockAIProvider()
    _override_generator(mock, db_session)
    try:
        response = await client.post(
            f"{STORIES_URL}/{story_id}/test-cases/generate",
            json={},
        )
    finally:
        app.dependency_overrides.pop(stories_ep.get_test_case_generator_service, None)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["story_id"] == story_id
    assert body["count"] == 8
    assert len(body["items"]) == 8
    assert body["provider"] == "mock-ai"
    categories = {item["category"] for item in body["items"]}
    assert categories == {
        "positive",
        "negative",
        "boundary",
        "api",
        "security",
        "database",
        "accessibility",
        "performance",
    }
    assert all(item["source"] == "ai" for item in body["items"])
    assert mock.calls == 1


@pytest.mark.asyncio
async def test_list_test_cases_paginated(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_project: Project,
):
    created = await client.post(STORIES_URL, json=_story_payload(seed_project.id))
    story_id = created.json()["id"]

    mock = MockAIProvider()
    _override_generator(mock, db_session)
    try:
        gen = await client.post(
            f"{STORIES_URL}/{story_id}/test-cases/generate",
            json={},
        )
        assert gen.status_code == 201

        listed = await client.get(
            f"{STORIES_URL}/{story_id}/test-cases",
            params={"page": 1, "page_size": 3},
        )
        filtered = await client.get(
            f"{STORIES_URL}/{story_id}/test-cases",
            params={"category": "security", "source": "ai"},
        )
    finally:
        app.dependency_overrides.pop(stories_ep.get_test_case_generator_service, None)

    assert listed.status_code == 200
    page_body = listed.json()
    assert page_body["total"] == 8
    assert page_body["page"] == 1
    assert page_body["page_size"] == 3
    assert len(page_body["items"]) == 3
    assert page_body["total_pages"] == 3

    assert filtered.status_code == 200
    sec = filtered.json()
    assert sec["total"] == 1
    assert sec["items"][0]["category"] == "security"


@pytest.mark.asyncio
async def test_generate_story_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
):
    mock = MockAIProvider()
    _override_generator(mock, db_session)
    try:
        response = await client.post(
            f"{STORIES_URL}/{uuid4()}/test-cases/generate",
            json={},
        )
    finally:
        app.dependency_overrides.pop(stories_ep.get_test_case_generator_service, None)

    assert response.status_code == 404
    assert mock.calls == 0


@pytest.mark.asyncio
async def test_generate_provider_failure(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_project: Project,
):
    created = await client.post(STORIES_URL, json=_story_payload(seed_project.id))
    story_id = created.json()["id"]

    mock = MockAIProvider(fail=True)
    _override_generator(mock, db_session)
    try:
        response = await client.post(
            f"{STORIES_URL}/{story_id}/test-cases/generate",
            json={},
        )
    finally:
        app.dependency_overrides.pop(stories_ep.get_test_case_generator_service, None)

    assert response.status_code == 400
    assert "AI test case generation failed" in response.json()["error"]["message"]


@pytest.mark.asyncio
async def test_parse_fenced_json_and_aliases(
    db_session: AsyncSession,
    seed_story: Story,
):
    fenced = (
        "Here:\n```json\n"
        + json.dumps(
            {
                "summary": "Minimal set",
                "test_cases": [
                    {
                        "title": "Happy login",
                        "type": "happy_path",
                        "steps": "Open login page",
                        "priority": "unknown",
                    },
                    "Bare string case",
                    {
                        "title": "A11y check",
                        "category": "a11y",
                        "steps": [{"step": "Use screen reader", "result": "Readable"}],
                    },
                ],
            }
        )
        + "\n```"
    )
    mock = MockAIProvider(content=fenced)
    service = TestCaseGeneratorService(db_session, provider=mock)
    result = await service.generate_test_cases(seed_story.id)

    assert result.count == 3
    assert result.items[0].category.value == "positive"
    assert result.items[0].steps[0]["action"] == "Open login page"
    assert result.items[1].title == "Bare string case"
    assert result.items[2].category.value == "accessibility"


@pytest.mark.asyncio
async def test_generate_includes_ac_and_analysis_in_prompt(
    db_session: AsyncSession,
    seed_story: Story,
):
    from app.models.story_analysis import StoryAnalysis

    db_session.add(
        AcceptanceCriteria(
            story_id=seed_story.id,
            description="User receives reset email within 1 minute",
            order_index=0,
        )
    )
    db_session.add(
        StoryAnalysis(
            story_id=seed_story.id,
            complexity="medium",
            risk="high",
            automation_candidate=True,
            dependencies=["Auth"],
            suggested_tests=[{"title": "Email arrives"}],
            summary="Focus on token expiry",
        )
    )
    await db_session.flush()

    captured = {}

    class CapturingProvider(MockAIProvider):
        async def generate(self, request: GenerateRequest) -> GenerateResponse:
            captured["prompt"] = request.messages[-1].content
            return await super().generate(request)

    mock = CapturingProvider()
    service = TestCaseGeneratorService(db_session, provider=mock)
    result = await service.generate_test_cases(seed_story.id)

    assert "User receives reset email within 1 minute" in captured["prompt"]
    assert "Focus on token expiry" in captured["prompt"]
    assert seed_story.title in captured["prompt"]
    # First mock case links to AC index 1
    assert result.items[0].acceptance_criteria_id is not None


@pytest.mark.asyncio
async def test_category_filter_on_generate(
    db_session: AsyncSession,
    seed_story: Story,
):
    mock = MockAIProvider()
    service = TestCaseGeneratorService(db_session, provider=mock)
    from app.models.enums import TestCaseCategory

    result = await service.generate_test_cases(
        seed_story.id,
        categories=[TestCaseCategory.SECURITY, TestCaseCategory.API],
    )
    assert result.count == 2
    cats = {item.category for item in result.items}
    assert cats == {TestCaseCategory.SECURITY, TestCaseCategory.API}


@pytest.mark.asyncio
async def test_test_case_generator_agent_emits_generated(
    db_session: AsyncSession,
    seed_story: Story,
):
    mock = MockAIProvider()
    agent = TestCaseGeneratorAgent(
        service_factory=lambda session: TestCaseGeneratorService(
            session, provider=mock
        )
    )
    context = AgentContext(
        run_id=uuid4(),
        project_id=seed_story.project_id,
        story_id=seed_story.id,
        workflow_state=WorkflowState.ANALYZED,
        correlation_id=uuid4(),
        session=db_session,
    )
    result = await agent.run(context)

    assert result.success is True
    assert result.emit_event == WorkflowEvent.TEST_CASES_GENERATED
    assert result.output["count"] == 8
    assert len(result.output["test_case_ids"]) == 8
    assert mock.calls == 1


def test_register_builtin_agents_registers_test_case_generator():
    registry = get_agent_registry()
    registry.clear()
    register_builtin_agents()
    agent = registry.get("test_case_generator")
    assert agent is not None
    assert WorkflowEvent.STORY_ANALYZED in agent.supported_events
    register_builtin_agents()
    assert registry.get("test_case_generator") is agent

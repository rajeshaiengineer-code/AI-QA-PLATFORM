"""
Unit / API tests for AI Story Analyzer.

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
from app.orchestration.agents.story_analyzer import StoryAnalyzerAgent
from app.orchestration.events.enums import WorkflowEvent
from app.orchestration.runtime import get_agent_registry, register_builtin_agents
from app.orchestration.state.enums import WorkflowState
from app.services.story_analyzer import StoryAnalyzerService


STORIES_URL = "/api/v1/stories"

MOCK_ANALYSIS = {
    "complexity": "medium",
    "risk": "high",
    "automation_candidate": True,
    "dependencies": ["Auth service", "Email provider"],
    "suggested_tests": [
        {
            "title": "Reset password with valid token",
            "type": "functional",
            "rationale": "Happy path",
        },
        {
            "title": "Reject expired reset token",
            "type": "negative",
            "rationale": "Security edge",
        },
    ],
    "summary": "Password reset via email token with expiry checks.",
    "notes": "Clarify token TTL with product.",
}


class MockAIProvider(BaseAIProvider):
    """Test double that returns fixed JSON analysis content."""

    def __init__(
        self,
        content: Optional[str] = None,
        *,
        fail: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key="test-key", **kwargs)
        self._content = content or json.dumps(MOCK_ANALYSIS)
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
        "external_id": "TST-ANALYZER-1",
    }
    data.update(overrides)
    return data


def _override_analyzer(mock: MockAIProvider, db_session: AsyncSession) -> None:
    def _dep() -> StoryAnalyzerService:
        return StoryAnalyzerService(db_session, provider=mock)

    app.dependency_overrides[stories_ep.get_story_analyzer_service] = _dep


@pytest.mark.asyncio
async def test_analyze_story_persists_result(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_project: Project,
):
    created = await client.post(STORIES_URL, json=_story_payload(seed_project.id))
    assert created.status_code == 201
    story_id = created.json()["id"]

    mock = MockAIProvider()
    _override_analyzer(mock, db_session)
    try:
        response = await client.post(f"{STORIES_URL}/{story_id}/analyze", json={})
    finally:
        app.dependency_overrides.pop(stories_ep.get_story_analyzer_service, None)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["story_id"] == story_id
    assert body["complexity"] == "medium"
    assert body["risk"] == "high"
    assert body["automation_candidate"] is True
    assert body["dependencies"] == ["Auth service", "Email provider"]
    assert len(body["suggested_tests"]) == 2
    assert "Password reset" in body["summary"]
    assert body["provider"] == "mock-ai"
    assert mock.calls == 1


@pytest.mark.asyncio
async def test_get_latest_analysis(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_project: Project,
):
    created = await client.post(STORIES_URL, json=_story_payload(seed_project.id))
    story_id = created.json()["id"]

    mock = MockAIProvider()
    _override_analyzer(mock, db_session)
    try:
        first = await client.post(f"{STORIES_URL}/{story_id}/analyze", json={})
        assert first.status_code == 201

        second_content = dict(MOCK_ANALYSIS)
        second_content["summary"] = "Second analysis run."
        second_content["complexity"] = "high"
        mock._content = json.dumps(second_content)
        second = await client.post(f"{STORIES_URL}/{story_id}/analyze", json={})
        assert second.status_code == 201

        latest = await client.get(f"{STORIES_URL}/{story_id}/analysis")
    finally:
        app.dependency_overrides.pop(stories_ep.get_story_analyzer_service, None)

    assert latest.status_code == 200
    body = latest.json()
    assert body["id"] == second.json()["id"]
    assert body["summary"] == "Second analysis run."
    assert body["complexity"] == "high"

@pytest.mark.asyncio
async def test_get_analysis_not_found(
    client: AsyncClient,
    seed_project: Project,
):
    created = await client.post(STORIES_URL, json=_story_payload(seed_project.id))
    story_id = created.json()["id"]

    response = await client.get(f"{STORIES_URL}/{story_id}/analysis")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_analyze_story_not_found(
    client: AsyncClient,
    db_session: AsyncSession,
):
    mock = MockAIProvider()
    _override_analyzer(mock, db_session)
    try:
        response = await client.post(f"{STORIES_URL}/{uuid4()}/analyze", json={})
    finally:
        app.dependency_overrides.pop(stories_ep.get_story_analyzer_service, None)

    assert response.status_code == 404
    assert mock.calls == 0


@pytest.mark.asyncio
async def test_analyze_provider_failure(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_project: Project,
):
    created = await client.post(STORIES_URL, json=_story_payload(seed_project.id))
    story_id = created.json()["id"]

    mock = MockAIProvider(fail=True)
    _override_analyzer(mock, db_session)
    try:
        response = await client.post(f"{STORIES_URL}/{story_id}/analyze", json={})
    finally:
        app.dependency_overrides.pop(stories_ep.get_story_analyzer_service, None)

    assert response.status_code == 400
    assert "AI analysis failed" in response.json()["error"]["message"]


@pytest.mark.asyncio
async def test_parse_fenced_json_and_string_tests(
    db_session: AsyncSession,
    seed_story: Story,
):
    fenced = (
        "Here you go:\n```json\n"
        + json.dumps(
            {
                "complexity": "low",
                "risk": "low",
                "automation_candidate": False,
                "dependencies": "Single service",
                "suggested_tests": ["Smoke login", {"title": "Logout"}],
                "summary": "Simple story",
                "notes": None,
            }
        )
        + "\n```"
    )
    mock = MockAIProvider(content=fenced)
    service = StoryAnalyzerService(db_session, provider=mock)
    result = await service.analyze_story(seed_story.id)

    assert result.complexity.value == "low"
    assert result.automation_candidate is False
    assert result.dependencies == ["Single service"]
    assert len(result.suggested_tests) == 2
    assert result.suggested_tests[0]["title"] == "Smoke login"


@pytest.mark.asyncio
async def test_analyze_includes_acceptance_criteria(
    db_session: AsyncSession,
    seed_story: Story,
):
    db_session.add(
        AcceptanceCriteria(
            story_id=seed_story.id,
            description="User receives reset email within 1 minute",
            order_index=0,
        )
    )
    await db_session.flush()

    captured = {}

    class CapturingProvider(MockAIProvider):
        async def generate(self, request: GenerateRequest) -> GenerateResponse:
            captured["prompt"] = request.messages[-1].content
            return await super().generate(request)

    mock = CapturingProvider()
    service = StoryAnalyzerService(db_session, provider=mock)
    await service.analyze_story(seed_story.id)

    assert "User receives reset email within 1 minute" in captured["prompt"]
    assert seed_story.title in captured["prompt"]


@pytest.mark.asyncio
async def test_story_analyzer_agent_emits_analyzed(
    db_session: AsyncSession,
    seed_story: Story,
):
    mock = MockAIProvider()
    agent = StoryAnalyzerAgent(
        service_factory=lambda session: StoryAnalyzerService(session, provider=mock)
    )
    context = AgentContext(
        run_id=uuid4(),
        project_id=seed_story.project_id,
        story_id=seed_story.id,
        workflow_state=WorkflowState.SYNCED,
        correlation_id=uuid4(),
        session=db_session,
    )
    result = await agent.run(context)

    assert result.success is True
    assert result.emit_event == WorkflowEvent.STORY_ANALYZED
    assert "analysis_id" in result.output
    assert mock.calls == 1


def test_register_builtin_agents_registers_story_analyzer():
    registry = get_agent_registry()
    registry.clear()
    register_builtin_agents()
    agent = registry.get("story_analyzer")
    assert agent is not None
    assert WorkflowEvent.STORY_IMPORTED in agent.supported_events
    assert WorkflowEvent.STORY_SYNCED in agent.supported_events
    # Idempotent
    register_builtin_agents()
    assert registry.get("story_analyzer") is agent

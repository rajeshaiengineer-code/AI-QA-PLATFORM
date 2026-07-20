"""
Unit / API tests for AI BDD Generator.

AI provider HTTP is mocked — no live API keys required.
"""

import json
from typing import Any, Optional, Union
from uuid import UUID, uuid4

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
from app.api.v1.endpoints import bdd as bdd_ep
from app.api.v1.endpoints import stories as stories_ep
from app.main import app
from app.models.enums import Priority, TestCaseSource, TestCaseStatus
from app.models.project import Project
from app.models.story import Story
from app.models.test_case import TestCase
from app.orchestration.agents.base import AgentContext
from app.orchestration.agents.bdd_generator import BddGeneratorAgent
from app.orchestration.events.enums import WorkflowEvent
from app.orchestration.runtime import get_agent_registry, register_builtin_agents
from app.orchestration.state.enums import WorkflowState
from app.schemas.bdd_feature import GherkinFeatureDraft
from app.services.bdd_generator import BddGeneratorService


STORIES_URL = "/api/v1/stories"
BDD_URL = "/api/v1/bdd"

MOCK_BDD = {
    "summary": "Password reset happy path and data-driven negatives.",
    "feature": {
        "name": "Password reset",
        "description": "Users can reset forgotten passwords",
        "tags": ["@auth", "smoke"],
        "scenarios": [
            {
                "type": "scenario",
                "name": "Reset with valid token",
                "tags": ["@positive"],
                "steps": [
                    {"keyword": "Given", "text": "a valid reset token exists"},
                    {"keyword": "When", "text": "the user submits a new password"},
                    {"keyword": "Then", "text": "the password is updated"},
                ],
            },
            {
                "type": "scenario_outline",
                "name": "Reject invalid tokens",
                "tags": ["@negative"],
                "steps": [
                    {"keyword": "Given", "text": "a token that is \"<state>\""},
                    {"keyword": "When", "text": "the user opens the reset link"},
                    {"keyword": "Then", "text": "an error \"<message>\" is shown"},
                ],
                "examples": {
                    "name": "Invalid token states",
                    "tags": ["@examples"],
                    "headers": ["state", "message"],
                    "rows": [
                        ["expired", "Token expired"],
                        ["revoked", "Token invalid"],
                    ],
                },
            },
        ],
    },
}


class MockAIProvider(BaseAIProvider):
    """Test double that returns fixed JSON BDD content."""

    def __init__(
        self,
        content: Optional[str] = None,
        *,
        fail: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key="test-key", **kwargs)
        self._content = content or json.dumps(MOCK_BDD)
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
        "external_id": "TST-BDD-1",
    }
    data.update(overrides)
    return data


def _override_bdd(mock: MockAIProvider, db_session: AsyncSession) -> None:
    def _dep() -> BddGeneratorService:
        return BddGeneratorService(db_session, provider=mock)

    app.dependency_overrides[stories_ep.get_bdd_generator_service] = _dep
    app.dependency_overrides[bdd_ep.get_bdd_generator_service] = _dep


async def _add_test_case(
    db_session: AsyncSession,
    story_id: Union[str, UUID],
    *,
    title: str = "Reset password with valid token",
    status: str = TestCaseStatus.APPROVED.value,
) -> TestCase:
    entity = TestCase(
        id=uuid4(),
        story_id=UUID(str(story_id)),
        title=title,
        description="Happy path",
        steps=[{"action": "Submit new password", "expected": "Success"}],
        expected_result="Password updated",
        priority=Priority.HIGH,
        order_index=0,
        category="positive",
        source=TestCaseSource.AI.value,
        status=status,
        tags=["auth"],
    )
    db_session.add(entity)
    await db_session.flush()
    return entity


@pytest.mark.asyncio
async def test_generate_bdd_from_approved(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_project: Project,
):
    created = await client.post(STORIES_URL, json=_story_payload(seed_project.id))
    assert created.status_code == 201
    story_id = created.json()["id"]
    await _add_test_case(db_session, story_id)

    mock = MockAIProvider()
    _override_bdd(mock, db_session)
    try:
        response = await client.post(
            f"{STORIES_URL}/{story_id}/bdd/generate",
            json={},
        )
    finally:
        app.dependency_overrides.pop(stories_ep.get_bdd_generator_service, None)
        app.dependency_overrides.pop(bdd_ep.get_bdd_generator_service, None)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["story_id"] == story_id
    assert body["source_test_case_count"] == 1
    assert body["provider"] == "mock-ai"
    feature = body["feature"]
    assert feature["name"] == "Password reset"
    assert "@auth" in feature["gherkin_content"]
    assert "Feature: Password reset" in feature["gherkin_content"]
    assert "Scenario: Reset with valid token" in feature["gherkin_content"]
    assert "Scenario Outline: Reject invalid tokens" in feature["gherkin_content"]
    assert "Examples:" in feature["gherkin_content"]
    assert "| state | message |" in feature["gherkin_content"]
    assert feature["include_drafts"] is False
    assert len(feature["scenarios"]) == 2
    assert mock.calls == 1


@pytest.mark.asyncio
async def test_generate_rejects_without_approved(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_project: Project,
):
    created = await client.post(STORIES_URL, json=_story_payload(seed_project.id))
    story_id = created.json()["id"]
    await _add_test_case(
        db_session,
        story_id,
        status=TestCaseStatus.PENDING_REVIEW.value,
    )

    mock = MockAIProvider()
    _override_bdd(mock, db_session)
    try:
        response = await client.post(
            f"{STORIES_URL}/{story_id}/bdd/generate",
            json={},
        )
    finally:
        app.dependency_overrides.pop(stories_ep.get_bdd_generator_service, None)
        app.dependency_overrides.pop(bdd_ep.get_bdd_generator_service, None)

    assert response.status_code == 400
    assert "approved" in response.json()["error"]["message"].lower()
    assert mock.calls == 0


@pytest.mark.asyncio
async def test_generate_with_include_drafts(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_project: Project,
):
    created = await client.post(STORIES_URL, json=_story_payload(seed_project.id))
    story_id = created.json()["id"]
    await _add_test_case(
        db_session,
        story_id,
        status=TestCaseStatus.DRAFT.value,
    )

    mock = MockAIProvider()
    _override_bdd(mock, db_session)
    try:
        response = await client.post(
            f"{STORIES_URL}/{story_id}/bdd/generate",
            json={"include_drafts": True},
        )
    finally:
        app.dependency_overrides.pop(stories_ep.get_bdd_generator_service, None)
        app.dependency_overrides.pop(bdd_ep.get_bdd_generator_service, None)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["feature"]["include_drafts"] is True
    assert body["source_test_case_count"] == 1


@pytest.mark.asyncio
async def test_list_and_get_bdd(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_project: Project,
):
    created = await client.post(STORIES_URL, json=_story_payload(seed_project.id))
    story_id = created.json()["id"]
    await _add_test_case(db_session, story_id)

    mock = MockAIProvider()
    _override_bdd(mock, db_session)
    try:
        gen = await client.post(f"{STORIES_URL}/{story_id}/bdd/generate", json={})
        assert gen.status_code == 201
        feature_id = gen.json()["feature"]["id"]

        listed = await client.get(f"{STORIES_URL}/{story_id}/bdd")
        fetched = await client.get(f"{BDD_URL}/{feature_id}")
    finally:
        app.dependency_overrides.pop(stories_ep.get_bdd_generator_service, None)
        app.dependency_overrides.pop(bdd_ep.get_bdd_generator_service, None)

    assert listed.status_code == 200
    page = listed.json()
    assert page["total"] == 1
    assert page["items"][0]["id"] == feature_id

    assert fetched.status_code == 200
    assert fetched.json()["id"] == feature_id
    assert fetched.json()["name"] == "Password reset"


@pytest.mark.asyncio
async def test_get_bdd_not_found(client: AsyncClient, db_session: AsyncSession):
    mock = MockAIProvider()
    _override_bdd(mock, db_session)
    try:
        response = await client.get(f"{BDD_URL}/{uuid4()}")
    finally:
        app.dependency_overrides.pop(stories_ep.get_bdd_generator_service, None)
        app.dependency_overrides.pop(bdd_ep.get_bdd_generator_service, None)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_story_not_found(client: AsyncClient, db_session: AsyncSession):
    mock = MockAIProvider()
    _override_bdd(mock, db_session)
    try:
        response = await client.post(
            f"{STORIES_URL}/{uuid4()}/bdd/generate",
            json={},
        )
    finally:
        app.dependency_overrides.pop(stories_ep.get_bdd_generator_service, None)
        app.dependency_overrides.pop(bdd_ep.get_bdd_generator_service, None)

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
    await _add_test_case(db_session, story_id)

    mock = MockAIProvider(fail=True)
    _override_bdd(mock, db_session)
    try:
        response = await client.post(
            f"{STORIES_URL}/{story_id}/bdd/generate",
            json={},
        )
    finally:
        app.dependency_overrides.pop(stories_ep.get_bdd_generator_service, None)
        app.dependency_overrides.pop(bdd_ep.get_bdd_generator_service, None)

    assert response.status_code == 400
    assert "AI BDD generation failed" in response.json()["error"]["message"]


@pytest.mark.asyncio
async def test_parse_fenced_json_and_render(
    db_session: AsyncSession,
    seed_story: Story,
):
    await _add_test_case(db_session, seed_story.id)
    fenced = (
        "Here:\n```json\n"
        + json.dumps(
            {
                "summary": "Minimal",
                "feature": {
                    "title": "Login",
                    "tags": "smoke",
                    "scenarios": [
                        {
                            "name": "Valid login",
                            "type": "scenario",
                            "steps": [
                                {"type": "given", "action": "I am on the login page"},
                                {"keyword": "when", "text": "I submit valid credentials"},
                                {"keyword": "Then", "step": "I see the dashboard"},
                            ],
                        }
                    ],
                },
            }
        )
        + "\n```"
    )
    mock = MockAIProvider(content=fenced)
    service = BddGeneratorService(db_session, provider=mock)
    result = await service.generate_bdd(seed_story.id)

    assert result.feature.name == "Login"
    assert "Feature: Login" in result.feature.gherkin_content
    assert "Given I am on the login page" in result.feature.gherkin_content
    assert "When I submit valid credentials" in result.feature.gherkin_content


def test_render_gherkin_tags_and_outline():
    draft = GherkinFeatureDraft.model_validate(MOCK_BDD["feature"])
    text = BddGeneratorService.render_gherkin(draft)
    assert text.startswith("@auth @smoke\nFeature: Password reset\n")
    assert "  @positive\n  Scenario: Reset with valid token\n" in text
    assert "  Scenario Outline: Reject invalid tokens\n" in text
    assert "    @examples\n    Examples: Invalid token states\n" in text
    assert "      | expired | Token expired |\n" in text


@pytest.mark.asyncio
async def test_prompt_includes_test_cases(
    db_session: AsyncSession,
    seed_story: Story,
):
    tc = await _add_test_case(db_session, seed_story.id, title="Unique TC Title XYZ")
    captured = {}

    class CapturingProvider(MockAIProvider):
        async def generate(self, request: GenerateRequest) -> GenerateResponse:
            captured["prompt"] = request.messages[-1].content
            return await super().generate(request)

    mock = CapturingProvider()
    service = BddGeneratorService(db_session, provider=mock)
    await service.generate_bdd(seed_story.id)

    assert "Unique TC Title XYZ" in captured["prompt"]
    assert str(tc.id) in captured["prompt"]
    assert seed_story.title in captured["prompt"]


@pytest.mark.asyncio
async def test_bdd_generator_agent_emits_generated(
    db_session: AsyncSession,
    seed_story: Story,
):
    await _add_test_case(db_session, seed_story.id)
    mock = MockAIProvider()
    agent = BddGeneratorAgent(
        service_factory=lambda session: BddGeneratorService(session, provider=mock)
    )
    context = AgentContext(
        run_id=uuid4(),
        project_id=seed_story.project_id,
        story_id=seed_story.id,
        workflow_state=WorkflowState.QA_APPROVED,
        correlation_id=uuid4(),
        session=db_session,
    )
    result = await agent.run(context)

    assert result.success is True
    assert result.emit_event == WorkflowEvent.BDD_GENERATED
    assert result.output["source_test_case_count"] == 1
    assert result.output["bdd_feature_id"]
    assert mock.calls == 1


def test_register_builtin_agents_registers_bdd_generator():
    registry = get_agent_registry()
    registry.clear()
    register_builtin_agents()
    agent = registry.get("bdd_generator")
    assert agent is not None
    assert WorkflowEvent.STORY_APPROVED in agent.supported_events
    register_builtin_agents()
    assert registry.get("bdd_generator") is agent

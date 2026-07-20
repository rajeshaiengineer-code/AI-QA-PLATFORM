"""
Unit / API tests for AI Playwright Generator.

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
from app.api.v1.endpoints import playwright as playwright_ep
from app.api.v1.endpoints import stories as stories_ep
from app.main import app
from app.models.bdd_feature import BddFeature
from app.models.enums import Priority, TestCaseSource, TestCaseStatus
from app.models.project import Project
from app.models.story import Story
from app.models.test_case import TestCase
from app.orchestration.agents.base import AgentContext
from app.orchestration.agents.playwright_generator import PlaywrightGeneratorAgent
from app.orchestration.events.enums import WorkflowEvent
from app.orchestration.runtime import get_agent_registry, register_builtin_agents
from app.orchestration.state.enums import WorkflowState
from app.services.playwright_generator import PlaywrightGeneratorService


STORIES_URL = "/api/v1/stories"
PLAYWRIGHT_URL = "/api/v1/playwright"

MOCK_PLAYWRIGHT = {
    "summary": "Password reset page object and happy-path spec.",
    "suite": {
        "name": "password-reset",
        "description": "Playwright suite for password reset",
        "language": "typescript",
        "framework": "playwright",
        "page_objects": [
            {
                "path": "pages/PasswordResetPage.ts",
                "content": (
                    "import { Page } from '@playwright/test';\n"
                    "export class PasswordResetPage {\n"
                    "  constructor(private page: Page) {}\n"
                    "  async submitNewPassword(password: string) {\n"
                    "    await this.page.getByLabel('New password').fill(password);\n"
                    "    await this.page.getByRole('button', { name: 'Submit' }).click();\n"
                    "  }\n"
                    "}\n"
                ),
                "description": "Password reset interactions",
            }
        ],
        "locators": [
            {
                "path": "locators/passwordReset.ts",
                "content": (
                    "export const passwordReset = {\n"
                    "  newPassword: 'New password',\n"
                    "  submit: 'Submit',\n"
                    "};\n"
                ),
            }
        ],
        "fixtures": [
            {
                "path": "fixtures/test.ts",
                "content": (
                    "import { test as base } from '@playwright/test';\n"
                    "import { PasswordResetPage } from '../pages/PasswordResetPage';\n"
                    "export const test = base.extend({\n"
                    "  passwordResetPage: async ({ page }, use) => {\n"
                    "    await use(new PasswordResetPage(page));\n"
                    "  },\n"
                    "});\n"
                ),
            }
        ],
        "utilities": [
            {
                "path": "utils/wait.ts",
                "content": (
                    "export async function waitForToast(page: any) {\n"
                    "  await page.getByRole('alert').waitFor();\n"
                    "}\n"
                ),
            }
        ],
        "assertions": [
            {
                "path": "assertions/password.ts",
                "content": (
                    "import { expect, Page } from '@playwright/test';\n"
                    "export async function expectPasswordUpdated(page: Page) {\n"
                    "  await expect(page.getByText('Password updated')).toBeVisible();\n"
                    "}\n"
                ),
            }
        ],
        "hooks": [
            {
                "path": "hooks/globalSetup.ts",
                "content": "export default async function globalSetup() {}\n",
            }
        ],
        "specs": [
            {
                "path": "tests/password-reset.spec.ts",
                "content": (
                    "import { test } from '../fixtures/test';\n"
                    "import { expectPasswordUpdated } from '../assertions/password';\n"
                    "test('reset with valid token', async ({ page, passwordResetPage }) => {\n"
                    "  await page.goto('/reset?token=valid');\n"
                    "  await passwordResetPage.submitNewPassword('Secure1!');\n"
                    "  await expectPasswordUpdated(page);\n"
                    "});\n"
                ),
            }
        ],
    },
}


class MockAIProvider(BaseAIProvider):
    """Test double that returns fixed JSON Playwright content."""

    def __init__(
        self,
        content: Optional[str] = None,
        *,
        fail: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(api_key="test-key", **kwargs)
        self._content = content or json.dumps(MOCK_PLAYWRIGHT)
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
        "external_id": "TST-PW-1",
    }
    data.update(overrides)
    return data


def _override_playwright(mock: MockAIProvider, db_session: AsyncSession) -> None:
    def _dep() -> PlaywrightGeneratorService:
        return PlaywrightGeneratorService(db_session, provider=mock)

    app.dependency_overrides[stories_ep.get_playwright_generator_service] = _dep
    app.dependency_overrides[playwright_ep.get_playwright_generator_service] = _dep


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


async def _add_bdd_feature(
    db_session: AsyncSession,
    story_id: Union[str, UUID],
    *,
    name: str = "Password reset",
) -> BddFeature:
    entity = BddFeature(
        id=uuid4(),
        story_id=UUID(str(story_id)),
        name=name,
        description="Users can reset forgotten passwords",
        gherkin_content=(
            "@auth\nFeature: Password reset\n"
            "  Scenario: Reset with valid token\n"
            "    Given a valid reset token\n"
            "    When the user submits a new password\n"
            "    Then the password is updated\n"
        ),
        tags=["@auth"],
        scenarios=[
            {
                "type": "scenario",
                "name": "Reset with valid token",
                "tags": ["@positive"],
                "steps": [
                    {"keyword": "Given", "text": "a valid reset token"},
                    {"keyword": "When", "text": "the user submits a new password"},
                    {"keyword": "Then", "text": "the password is updated"},
                ],
            }
        ],
        source_test_case_ids=[],
        include_drafts=False,
    )
    db_session.add(entity)
    await db_session.flush()
    return entity


@pytest.mark.asyncio
async def test_generate_from_bdd_and_test_cases(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_project: Project,
):
    created = await client.post(STORIES_URL, json=_story_payload(seed_project.id))
    assert created.status_code == 201
    story_id = created.json()["id"]
    await _add_test_case(db_session, story_id)
    await _add_bdd_feature(db_session, story_id)

    mock = MockAIProvider()
    _override_playwright(mock, db_session)
    try:
        response = await client.post(
            f"{STORIES_URL}/{story_id}/playwright/generate",
            json={},
        )
    finally:
        app.dependency_overrides.pop(
            stories_ep.get_playwright_generator_service, None
        )
        app.dependency_overrides.pop(
            playwright_ep.get_playwright_generator_service, None
        )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["story_id"] == story_id
    assert body["source_test_case_count"] == 1
    assert body["source_bdd_feature_count"] == 1
    assert body["file_count"] == 7
    assert body["provider"] == "mock-ai"
    artifact = body["artifact"]
    assert artifact["name"] == "password-reset"
    assert artifact["language"] == "typescript"
    assert artifact["framework"] == "playwright"
    assert len(artifact["page_objects"]) == 1
    assert "PasswordResetPage" in artifact["page_objects"][0]["content"]
    assert len(artifact["locators"]) == 1
    assert len(artifact["fixtures"]) == 1
    assert len(artifact["utilities"]) == 1
    assert len(artifact["assertions"]) == 1
    assert len(artifact["hooks"]) == 1
    assert len(artifact["specs"]) == 1
    assert mock.calls == 1


@pytest.mark.asyncio
async def test_generate_from_test_cases_only(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_project: Project,
):
    created = await client.post(STORIES_URL, json=_story_payload(seed_project.id))
    story_id = created.json()["id"]
    await _add_test_case(db_session, story_id)

    mock = MockAIProvider()
    _override_playwright(mock, db_session)
    try:
        response = await client.post(
            f"{STORIES_URL}/{story_id}/playwright/generate",
            json={"use_bdd": False, "use_test_cases": True},
        )
    finally:
        app.dependency_overrides.pop(
            stories_ep.get_playwright_generator_service, None
        )
        app.dependency_overrides.pop(
            playwright_ep.get_playwright_generator_service, None
        )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source_bdd_feature_count"] == 0
    assert body["source_test_case_count"] == 1
    assert body["artifact"]["use_bdd"] is False


@pytest.mark.asyncio
async def test_generate_from_bdd_only(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_project: Project,
):
    created = await client.post(STORIES_URL, json=_story_payload(seed_project.id))
    story_id = created.json()["id"]
    await _add_bdd_feature(db_session, story_id)

    mock = MockAIProvider()
    _override_playwright(mock, db_session)
    try:
        response = await client.post(
            f"{STORIES_URL}/{story_id}/playwright/generate",
            json={"use_bdd": True, "use_test_cases": False},
        )
    finally:
        app.dependency_overrides.pop(
            stories_ep.get_playwright_generator_service, None
        )
        app.dependency_overrides.pop(
            playwright_ep.get_playwright_generator_service, None
        )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["source_bdd_feature_count"] == 1
    assert body["source_test_case_count"] == 0


@pytest.mark.asyncio
async def test_generate_rejects_without_sources(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_project: Project,
):
    created = await client.post(STORIES_URL, json=_story_payload(seed_project.id))
    story_id = created.json()["id"]

    mock = MockAIProvider()
    _override_playwright(mock, db_session)
    try:
        response = await client.post(
            f"{STORIES_URL}/{story_id}/playwright/generate",
            json={},
        )
    finally:
        app.dependency_overrides.pop(
            stories_ep.get_playwright_generator_service, None
        )
        app.dependency_overrides.pop(
            playwright_ep.get_playwright_generator_service, None
        )

    assert response.status_code == 400
    assert mock.calls == 0


@pytest.mark.asyncio
async def test_generate_rejects_unapproved_when_test_cases_only(
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
    _override_playwright(mock, db_session)
    try:
        response = await client.post(
            f"{STORIES_URL}/{story_id}/playwright/generate",
            json={"use_bdd": False, "use_test_cases": True},
        )
    finally:
        app.dependency_overrides.pop(
            stories_ep.get_playwright_generator_service, None
        )
        app.dependency_overrides.pop(
            playwright_ep.get_playwright_generator_service, None
        )

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
    _override_playwright(mock, db_session)
    try:
        response = await client.post(
            f"{STORIES_URL}/{story_id}/playwright/generate",
            json={
                "use_bdd": False,
                "use_test_cases": True,
                "include_drafts": True,
            },
        )
    finally:
        app.dependency_overrides.pop(
            stories_ep.get_playwright_generator_service, None
        )
        app.dependency_overrides.pop(
            playwright_ep.get_playwright_generator_service, None
        )

    assert response.status_code == 201, response.text
    assert response.json()["artifact"]["include_drafts"] is True


@pytest.mark.asyncio
async def test_list_and_get_playwright(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_project: Project,
):
    created = await client.post(STORIES_URL, json=_story_payload(seed_project.id))
    story_id = created.json()["id"]
    await _add_test_case(db_session, story_id)

    mock = MockAIProvider()
    _override_playwright(mock, db_session)
    try:
        gen = await client.post(
            f"{STORIES_URL}/{story_id}/playwright/generate",
            json={"use_bdd": False},
        )
        assert gen.status_code == 201
        artifact_id = gen.json()["artifact"]["id"]

        listed = await client.get(f"{STORIES_URL}/{story_id}/playwright")
        fetched = await client.get(f"{PLAYWRIGHT_URL}/{artifact_id}")
    finally:
        app.dependency_overrides.pop(
            stories_ep.get_playwright_generator_service, None
        )
        app.dependency_overrides.pop(
            playwright_ep.get_playwright_generator_service, None
        )

    assert listed.status_code == 200
    page = listed.json()
    assert page["total"] == 1
    assert page["items"][0]["id"] == artifact_id

    assert fetched.status_code == 200
    assert fetched.json()["id"] == artifact_id
    assert fetched.json()["name"] == "password-reset"


@pytest.mark.asyncio
async def test_get_playwright_not_found(client: AsyncClient, db_session: AsyncSession):
    mock = MockAIProvider()
    _override_playwright(mock, db_session)
    try:
        response = await client.get(f"{PLAYWRIGHT_URL}/{uuid4()}")
    finally:
        app.dependency_overrides.pop(
            stories_ep.get_playwright_generator_service, None
        )
        app.dependency_overrides.pop(
            playwright_ep.get_playwright_generator_service, None
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_story_not_found(client: AsyncClient, db_session: AsyncSession):
    mock = MockAIProvider()
    _override_playwright(mock, db_session)
    try:
        response = await client.post(
            f"{STORIES_URL}/{uuid4()}/playwright/generate",
            json={},
        )
    finally:
        app.dependency_overrides.pop(
            stories_ep.get_playwright_generator_service, None
        )
        app.dependency_overrides.pop(
            playwright_ep.get_playwright_generator_service, None
        )

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
    _override_playwright(mock, db_session)
    try:
        response = await client.post(
            f"{STORIES_URL}/{story_id}/playwright/generate",
            json={"use_bdd": False},
        )
    finally:
        app.dependency_overrides.pop(
            stories_ep.get_playwright_generator_service, None
        )
        app.dependency_overrides.pop(
            playwright_ep.get_playwright_generator_service, None
        )

    assert response.status_code == 400
    assert "AI Playwright generation failed" in response.json()["error"]["message"]


@pytest.mark.asyncio
async def test_parse_fenced_json_and_aliases(
    db_session: AsyncSession,
    seed_story: Story,
):
    await _add_test_case(db_session, seed_story.id)
    fenced = (
        "Here:\n```json\n"
        + json.dumps(
            {
                "summary": "Minimal",
                "suite": {
                    "title": "login-suite",
                    "pages": [
                        {
                            "file": "pages/LoginPage.ts",
                            "code": "export class LoginPage {}",
                        }
                    ],
                    "tests": [
                        {
                            "path": "tests/login.spec.ts",
                            "source": "import { test } from '@playwright/test';",
                        }
                    ],
                },
            }
        )
        + "\n```"
    )
    mock = MockAIProvider(content=fenced)
    service = PlaywrightGeneratorService(db_session, provider=mock)
    result = await service.generate_playwright(
        seed_story.id,
        use_bdd=False,
        use_test_cases=True,
    )

    assert result.artifact.name == "login-suite"
    assert result.file_count == 2
    assert result.artifact.page_objects[0]["path"] == "pages/LoginPage.ts"
    assert result.artifact.specs[0]["path"] == "tests/login.spec.ts"


@pytest.mark.asyncio
async def test_prompt_includes_sources(
    db_session: AsyncSession,
    seed_story: Story,
):
    tc = await _add_test_case(db_session, seed_story.id, title="Unique TC Title XYZ")
    feat = await _add_bdd_feature(db_session, seed_story.id, name="Unique Feature XYZ")
    captured = {}

    class CapturingProvider(MockAIProvider):
        async def generate(self, request: GenerateRequest) -> GenerateResponse:
            captured["prompt"] = request.messages[-1].content
            return await super().generate(request)

    mock = CapturingProvider()
    service = PlaywrightGeneratorService(db_session, provider=mock)
    await service.generate_playwright(seed_story.id)

    assert "Unique TC Title XYZ" in captured["prompt"]
    assert str(tc.id) in captured["prompt"]
    assert "Unique Feature XYZ" in captured["prompt"]
    assert str(feat.id) in captured["prompt"]
    assert seed_story.title in captured["prompt"]


@pytest.mark.asyncio
async def test_playwright_generator_agent_emits_generated(
    db_session: AsyncSession,
    seed_story: Story,
):
    await _add_test_case(db_session, seed_story.id)
    await _add_bdd_feature(db_session, seed_story.id)
    mock = MockAIProvider()
    agent = PlaywrightGeneratorAgent(
        service_factory=lambda session: PlaywrightGeneratorService(
            session, provider=mock
        )
    )
    context = AgentContext(
        run_id=uuid4(),
        project_id=seed_story.project_id,
        story_id=seed_story.id,
        workflow_state=WorkflowState.BDD_GENERATED,
        correlation_id=uuid4(),
        session=db_session,
    )
    result = await agent.run(context)

    assert result.success is True
    assert result.emit_event == WorkflowEvent.AUTOMATION_GENERATED
    assert result.output["file_count"] == 7
    assert result.output["automation_artifact_id"]
    assert mock.calls == 1


def test_register_builtin_agents_registers_playwright_generator():
    registry = get_agent_registry()
    registry.clear()
    register_builtin_agents()
    agent = registry.get("playwright_generator")
    assert agent is not None
    assert WorkflowEvent.BDD_GENERATED in agent.supported_events
    register_builtin_agents()
    assert registry.get("playwright_generator") is agent

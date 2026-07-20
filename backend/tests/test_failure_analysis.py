"""
Tests for AI Failure Analysis — mocked AI provider, persistence, APIs, agent.
"""

from __future__ import annotations

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
from app.api.v1.endpoints import executions as executions_ep
from app.main import app
from app.models.automation_job import AutomationJob
from app.models.enums import AutomationStatus, ExecutionStatus, TestCaseStatus
from app.models.execution import Execution
from app.models.project import Project
from app.models.story import Story
from app.models.test_case import TestCase
from app.orchestration.agents.base import AgentContext
from app.orchestration.agents.failure_analysis import FailureAnalysisAgent
from app.orchestration.events.enums import WorkflowEvent
from app.orchestration.runtime import get_agent_registry, register_builtin_agents
from app.orchestration.state.enums import WorkflowState
from app.orchestration.state.transitions import transition_for
from app.services.failure_analyzer import FailureAnalyzerService

MOCK_ANALYSIS = {
    "category": "product_bug",
    "is_flaky": False,
    "is_product_bug": True,
    "summary": "Empty password submits and returns 500.",
    "root_cause": "Missing client validation; API does not guard empty password.",
    "suggested_fix": "Add required validation and return 400 from the API.",
    "confidence": 0.88,
    "notes": "Screenshot shows blank password field.",
}


class MockAIProvider(BaseAIProvider):
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


def _override_analyzer(mock: MockAIProvider, db_session: AsyncSession) -> None:
    def _dep() -> FailureAnalyzerService:
        return FailureAnalyzerService(db_session, provider=mock)

    app.dependency_overrides[executions_ep.get_failure_analyzer_service] = _dep


async def _seed_failed_execution(
    db_session: AsyncSession,
    story: Story,
) -> Execution:
    case = TestCase(
        id=uuid4(),
        story_id=story.id,
        title="Should fail on empty password",
        status=TestCaseStatus.APPROVED.value,
        steps=[{"action": "Submit empty password", "expected": "Validation error"}],
        expected_result="Show validation error",
        order_index=0,
    )
    db_session.add(case)
    await db_session.flush()

    job = AutomationJob(
        id=uuid4(),
        project_id=story.project_id,
        name="Failure analysis job",
        status=AutomationStatus.FAILED,
        config={"story_id": str(story.id)},
    )
    db_session.add(job)
    await db_session.flush()

    execution = Execution(
        id=uuid4(),
        automation_job_id=job.id,
        test_case_id=case.id,
        status=ExecutionStatus.FAILED,
        error_message="AssertionError: expected 400 got 500",
        stack_trace="Traceback (most recent call last):\n  ...",
        evidence_url="stub://evidence/fail.png",
        retry_count=0,
    )
    db_session.add(execution)
    await db_session.flush()
    return execution


def test_failure_analysis_workflow_transitions():
    assert (
        transition_for(
            WorkflowState.EXECUTION_COMPLETED,
            WorkflowEvent.FAILURE_ANALYZED,
        )
        == WorkflowState.FAILURE_ANALYZED
    )
    assert (
        transition_for(
            WorkflowState.FAILURE_ANALYZED,
            WorkflowEvent.REPORT_PUBLISHED,
        )
        == WorkflowState.COMPLETED
    )


@pytest.mark.asyncio
async def test_analyze_failure_persists_result(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_story: Story,
):
    execution = await _seed_failed_execution(db_session, seed_story)
    mock = MockAIProvider()
    _override_analyzer(mock, db_session)
    try:
        response = await client.post(
            f"/api/v1/executions/{execution.id}/analyze-failure",
            json={
                "logs": "stub://logs/run-1.txt",
                "screenshot_url": "stub://screenshots/fail-1.png",
                "video_url": "stub://videos/fail-1.webm",
                "network_url": "stub://network/fail-1.har",
                "trace_url": "stub://traces/fail-1.zip",
            },
        )
    finally:
        app.dependency_overrides.pop(
            executions_ep.get_failure_analyzer_service,
            None,
        )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["execution_id"] == str(execution.id)
    assert body["category"] == "product_bug"
    assert body["is_product_bug"] is True
    assert body["suggested_fix"]
    assert "validation" in body["suggested_fix"].lower() or body["suggested_fix"]
    assert body["logs"] == "stub://logs/run-1.txt"
    assert body["screenshot_url"] == "stub://screenshots/fail-1.png"
    assert body["provider"] == "mock-ai"
    assert mock.calls == 1


@pytest.mark.asyncio
async def test_get_latest_failure_analysis(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_story: Story,
):
    execution = await _seed_failed_execution(db_session, seed_story)
    mock = MockAIProvider()
    _override_analyzer(mock, db_session)
    try:
        created = await client.post(
            f"/api/v1/executions/{execution.id}/analyze-failure",
            json={},
        )
        assert created.status_code == 201
        fetched = await client.get(
            f"/api/v1/executions/{execution.id}/failure-analysis",
        )
    finally:
        app.dependency_overrides.pop(
            executions_ep.get_failure_analyzer_service,
            None,
        )

    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["id"] == created.json()["id"]
    assert fetched.json()["root_cause"]


@pytest.mark.asyncio
async def test_analyze_passed_execution_rejected(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_story: Story,
):
    case = TestCase(
        id=uuid4(),
        story_id=seed_story.id,
        title="Happy path",
        status=TestCaseStatus.APPROVED.value,
    )
    db_session.add(case)
    await db_session.flush()
    job = AutomationJob(
        id=uuid4(),
        project_id=seed_story.project_id,
        name="pass job",
        status=AutomationStatus.COMPLETED,
    )
    db_session.add(job)
    await db_session.flush()
    execution = Execution(
        id=uuid4(),
        automation_job_id=job.id,
        test_case_id=case.id,
        status=ExecutionStatus.PASSED,
    )
    db_session.add(execution)
    await db_session.flush()

    mock = MockAIProvider()
    _override_analyzer(mock, db_session)
    try:
        response = await client.post(
            f"/api/v1/executions/{execution.id}/analyze-failure",
            json={},
        )
    finally:
        app.dependency_overrides.pop(
            executions_ep.get_failure_analyzer_service,
            None,
        )

    assert response.status_code == 400
    assert mock.calls == 0


@pytest.mark.asyncio
async def test_failure_analysis_agent_emits_event(
    db_session: AsyncSession,
    seed_story: Story,
    seed_project: Project,
):
    execution = await _seed_failed_execution(db_session, seed_story)
    mock = MockAIProvider()
    agent = FailureAnalysisAgent(
        service_factory=lambda s: FailureAnalyzerService(s, provider=mock),
    )
    context = AgentContext(
        run_id=uuid4(),
        organization_id=seed_project.organization_id,
        project_id=seed_project.id,
        story_id=seed_story.id,
        workflow_state=WorkflowState.EXECUTION_COMPLETED,
        correlation_id=uuid4(),
        input={"execution_id": str(execution.id)},
        session=db_session,
    )
    result = await agent.run(context)
    assert result.success is True
    assert result.emit_event == WorkflowEvent.FAILURE_ANALYZED
    assert result.output["analyzed"] == 1
    assert mock.calls == 1


@pytest.mark.asyncio
async def test_builtin_registers_failure_analysis_agent():
    registry = get_agent_registry()
    registry.clear()
    register_builtin_agents()
    try:
        assert registry.get("failure_analysis") is not None
        agents = registry.resolve(WorkflowEvent.EXECUTION_COMPLETED)
        assert any(a.name == "failure_analysis" for a in agents)
    finally:
        registry.clear()

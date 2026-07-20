"""
Tests for Jira Bug Creation — mocked Jira HTTP, persistence, APIs, agent.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints import executions as executions_ep
from app.connectors.base.types import (
    ConnectorEnvironment,
    CredentialType,
)
from app.connectors.config.models import ConnectorConfig
from app.connectors.credentials.models import ConnectorCredentials
from app.connectors.jira.client import JiraClient
from app.connectors.jira.connector import JiraConnector
from app.main import app
from app.models.automation_job import AutomationJob
from app.models.enums import (
    AutomationStatus,
    ExecutionStatus,
    FailureCategory,
    TestCaseStatus,
)
from app.models.execution import Execution
from app.models.failure_analysis import FailureAnalysis
from app.models.project import Project
from app.models.story import Story
from app.models.test_case import TestCase
from app.orchestration.agents.base import AgentContext
from app.orchestration.agents.bug_creation import BugCreationAgent
from app.orchestration.events.enums import WorkflowEvent
from app.orchestration.runtime import get_agent_registry, register_builtin_agents
from app.orchestration.state.enums import WorkflowState
from app.orchestration.state.transitions import transition_for
from app.services.bug_creation import BugCreationService


class MockJiraClient(JiraClient):
    """JiraClient double that records create_issue calls without HTTP."""

    def __init__(self) -> None:
        super().__init__(
            base_url="https://acme.atlassian.net",
            email="qa@example.com",
            api_token="token",
        )
        self.create_calls: List[Dict[str, Any]] = []
        self._next_key = "QA-42"

    async def open(self) -> None:
        return None

    async def close(self) -> None:
        return None

    async def get_myself(self) -> Dict[str, Any]:
        return {"accountId": "acc-1", "displayName": "QA Bot"}

    async def create_issue(
        self,
        *,
        project_key: str,
        summary: str,
        description: Optional[str] = None,
        issue_type: str = "Bug",
        priority_name: Optional[str] = None,
        labels: Optional[List[str]] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = {
            "project_key": project_key,
            "summary": summary,
            "description": description,
            "issue_type": issue_type,
            "priority_name": priority_name,
            "labels": labels,
            "extra_fields": extra_fields,
        }
        self.create_calls.append(payload)
        key = self._next_key
        return {"id": "10042", "key": key, "self": "/rest/api/3/issue/10042"}


def _build_mock_connector(client: MockJiraClient) -> JiraConnector:
    config = ConnectorConfig(
        connector_name="jira",
        environment=ConnectorEnvironment.DEVELOPMENT,
        settings={"base_url": "https://acme.atlassian.net"},
        enabled=True,
    )
    credentials = ConnectorCredentials(
        connector_name="jira",
        credential_type=CredentialType.USERNAME_PASSWORD,
        username="qa@example.com",
        password="token",
    )
    connector = JiraConnector(config=config, credentials=credentials)
    connector._client = client
    connector._connected = True
    return connector


def _override_bug_service(
    db_session: AsyncSession,
    connector: JiraConnector,
) -> None:
    def _dep() -> BugCreationService:
        return BugCreationService(db_session, connector=connector)

    app.dependency_overrides[executions_ep.get_bug_creation_service] = _dep


async def _seed_failed_with_analysis(
    db_session: AsyncSession,
    story: Story,
) -> tuple:
    case = TestCase(
        id=uuid4(),
        story_id=story.id,
        title="Should fail on empty password",
        status=TestCaseStatus.APPROVED.value,
        order_index=0,
    )
    db_session.add(case)
    await db_session.flush()

    job = AutomationJob(
        id=uuid4(),
        project_id=story.project_id,
        name="Bug creation job",
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
        error_message="expected 400 got 500",
        stack_trace="stack...",
        retry_count=0,
    )
    db_session.add(execution)
    await db_session.flush()

    analysis = FailureAnalysis(
        id=uuid4(),
        execution_id=execution.id,
        category=FailureCategory.PRODUCT_BUG.value,
        is_flaky=False,
        is_product_bug=True,
        summary="Empty password returns 500",
        root_cause="Missing API validation",
        suggested_fix="Return 400 for empty password",
        confidence=0.9,
        logs="stub://logs/run-1.txt",
        screenshot_url="stub://screenshots/fail-1.png",
    )
    db_session.add(analysis)
    await db_session.flush()
    return execution, analysis


def test_bug_created_workflow_transition():
    assert (
        transition_for(
            WorkflowState.FAILURE_ANALYZED,
            WorkflowEvent.BUG_CREATED,
        )
        == WorkflowState.COMPLETED
    )


@pytest.mark.asyncio
async def test_create_jira_bug_persists_local_bug(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_story: Story,
):
    execution, analysis = await _seed_failed_with_analysis(db_session, seed_story)
    mock_client = MockJiraClient()
    connector = _build_mock_connector(mock_client)
    _override_bug_service(db_session, connector)
    try:
        response = await client.post(
            f"/api/v1/executions/{execution.id}/create-jira-bug",
            json={
                "jira_project_key": "QA",
                "failure_analysis_id": str(analysis.id),
                "logs_url": "stub://logs/run-1.txt",
                "execution_url": f"/api/v1/executions/{execution.id}",
                "priority": "high",
                "labels": ["ai-qa", "auto-filed"],
            },
        )
    finally:
        app.dependency_overrides.pop(executions_ep.get_bug_creation_service, None)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["jira_key"] == "QA-42"
    assert body["jira_id"] == "10042"
    assert body["jira_url"] == "https://acme.atlassian.net/browse/QA-42"
    bug = body["bug"]
    assert bug["external_id"] == "QA-42"
    assert bug["execution_id"] == str(execution.id)
    assert bug["failure_analysis_id"] == str(analysis.id)
    assert bug["extra_metadata"]["logs_url"] == "stub://logs/run-1.txt"
    assert bug["extra_metadata"]["execution_url"] == (
        f"/api/v1/executions/{execution.id}"
    )
    assert bug["extra_metadata"]["summary"]
    assert len(mock_client.create_calls) == 1
    assert mock_client.create_calls[0]["project_key"] == "QA"
    assert mock_client.create_calls[0]["issue_type"] == "Bug"
    assert "Empty password" in mock_client.create_calls[0]["summary"]


@pytest.mark.asyncio
async def test_create_jira_bug_uses_latest_analysis(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_story: Story,
):
    execution, _analysis = await _seed_failed_with_analysis(db_session, seed_story)
    mock_client = MockJiraClient()
    connector = _build_mock_connector(mock_client)
    _override_bug_service(db_session, connector)
    try:
        response = await client.post(
            f"/api/v1/executions/{execution.id}/create-jira-bug",
            json={"jira_project_key": "QA"},
        )
    finally:
        app.dependency_overrides.pop(executions_ep.get_bug_creation_service, None)

    assert response.status_code == 201, response.text
    assert response.json()["bug"]["failure_analysis_id"] is not None
    assert mock_client.create_calls


@pytest.mark.asyncio
async def test_create_jira_bug_rejects_passed_execution(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_story: Story,
):
    case = TestCase(
        id=uuid4(),
        story_id=seed_story.id,
        title="pass",
        status=TestCaseStatus.APPROVED.value,
    )
    db_session.add(case)
    await db_session.flush()
    job = AutomationJob(
        id=uuid4(),
        project_id=seed_story.project_id,
        name="pass",
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

    mock_client = MockJiraClient()
    connector = _build_mock_connector(mock_client)
    _override_bug_service(db_session, connector)
    try:
        response = await client.post(
            f"/api/v1/executions/{execution.id}/create-jira-bug",
            json={"jira_project_key": "QA"},
        )
    finally:
        app.dependency_overrides.pop(executions_ep.get_bug_creation_service, None)

    assert response.status_code == 400
    assert mock_client.create_calls == []


def test_jira_client_adf_helper():
    adf = JiraClient._plain_text_to_adf("line1\nline2")
    assert adf["type"] == "doc"
    assert len(adf["content"]) == 2


@pytest.mark.asyncio
async def test_bug_creation_agent(
    db_session: AsyncSession,
    seed_story: Story,
    seed_project: Project,
):
    execution, analysis = await _seed_failed_with_analysis(db_session, seed_story)
    mock_client = MockJiraClient()
    connector = _build_mock_connector(mock_client)
    agent = BugCreationAgent(
        service_factory=lambda s: BugCreationService(s, connector=connector),
    )
    context = AgentContext(
        run_id=uuid4(),
        organization_id=seed_project.organization_id,
        project_id=seed_project.id,
        story_id=seed_story.id,
        workflow_state=WorkflowState.FAILURE_ANALYZED,
        correlation_id=uuid4(),
        input={
            "jira_project_key": "QA",
            "execution_ids": [str(execution.id)],
            "analysis_ids": [str(analysis.id)],
        },
        session=db_session,
    )
    result = await agent.run(context)
    assert result.success is True
    assert result.emit_event == WorkflowEvent.BUG_CREATED
    assert result.output["created"] == 1
    assert result.output["jira_keys"] == ["QA-42"]


@pytest.mark.asyncio
async def test_bug_creation_agent_skips_without_project_key(
    db_session: AsyncSession,
    seed_story: Story,
    seed_project: Project,
):
    agent = BugCreationAgent()
    context = AgentContext(
        run_id=uuid4(),
        organization_id=seed_project.organization_id,
        project_id=seed_project.id,
        story_id=seed_story.id,
        workflow_state=WorkflowState.FAILURE_ANALYZED,
        correlation_id=uuid4(),
        input={"execution_ids": [str(uuid4())]},
        session=db_session,
    )
    result = await agent.run(context)
    assert result.success is True
    assert result.emit_event == WorkflowEvent.REPORT_PUBLISHED


@pytest.mark.asyncio
async def test_builtin_registers_bug_creation_agent():
    registry = get_agent_registry()
    registry.clear()
    register_builtin_agents()
    try:
        assert registry.get("bug_creation") is not None
        agents = registry.resolve(WorkflowEvent.FAILURE_ANALYZED)
        assert any(a.name == "bug_creation" for a in agents)
    finally:
        registry.clear()

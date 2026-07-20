"""
Tests for Execution Engine — stub runner, persistence, APIs, workflow events.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.execution.stub_runner import StubTestRunner
from app.models.automation_artifact import AutomationArtifact
from app.models.enums import AutomationStatus, ExecutionStatus, TestCaseStatus
from app.models.project import Project
from app.models.story import Story
from app.models.test_case import TestCase
from app.orchestration.events.enums import WorkflowEvent
from app.orchestration.state.enums import WorkflowState
from app.orchestration.state.transitions import transition_for


class _FakeCase:
    def __init__(self, title: str) -> None:
        self.id = uuid4()
        self.title = title


class TestStubRunner:
    def test_passes_by_default(self):
        runner = StubTestRunner()
        case = _FakeCase("Happy path login")
        results = runner.run([case])
        assert len(results) == 1
        assert results[0].status == ExecutionStatus.PASSED
        assert results[0].duration_ms is not None

    def test_fails_on_title_keyword(self):
        runner = StubTestRunner()
        case = _FakeCase("Should fail when password empty")
        results = runner.run([case])
        assert results[0].status == ExecutionStatus.FAILED
        assert results[0].error_message is not None

    def test_force_fail_ids(self):
        runner = StubTestRunner()
        case = _FakeCase("Always pass title")
        results = runner.run(
            [case],
            config={"force_fail_test_case_ids": [str(case.id)]},
        )
        assert results[0].status == ExecutionStatus.FAILED


def test_execution_workflow_transitions():
    assert (
        transition_for(WorkflowState.PR_CREATED, WorkflowEvent.EXECUTION_STARTED)
        == WorkflowState.EXECUTION_STARTED
    )
    assert (
        transition_for(
            WorkflowState.EXECUTION_STARTED,
            WorkflowEvent.EXECUTION_COMPLETED,
        )
        == WorkflowState.EXECUTION_COMPLETED
    )


async def _seed_approved_cases(
    db_session: AsyncSession,
    story: Story,
) -> list[TestCase]:
    cases = [
        TestCase(
            id=uuid4(),
            story_id=story.id,
            title="Login succeeds with valid credentials",
            status=TestCaseStatus.APPROVED.value,
            order_index=0,
        ),
        TestCase(
            id=uuid4(),
            story_id=story.id,
            title="Should fail on invalid token",
            status=TestCaseStatus.APPROVED.value,
            order_index=1,
        ),
        TestCase(
            id=uuid4(),
            story_id=story.id,
            title="Draft case ignored",
            status=TestCaseStatus.DRAFT.value,
            order_index=2,
        ),
    ]
    for case in cases:
        db_session.add(case)
    await db_session.flush()
    return cases


@pytest.mark.asyncio
async def test_run_by_story_persists_results(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_story: Story,
):
    cases = await _seed_approved_cases(db_session, seed_story)

    response = await client.post(
        "/api/v1/executions/run",
        json={"story_id": str(seed_story.id)},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["runner"] == "stub"
    job = body["job"]
    assert job["status"] == AutomationStatus.FAILED.value  # one forced-by-title fail
    assert job["total"] == 2  # draft excluded
    assert job["passed"] == 1
    assert job["failed"] == 1
    assert len(job["executions"]) == 2

    statuses = {ex["test_case_id"]: ex["status"] for ex in job["executions"]}
    assert statuses[str(cases[0].id)] == ExecutionStatus.PASSED.value
    assert statuses[str(cases[1].id)] == ExecutionStatus.FAILED.value


@pytest.mark.asyncio
async def test_run_by_artifact(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_story: Story,
):
    cases = await _seed_approved_cases(db_session, seed_story)
    artifact = AutomationArtifact(
        id=uuid4(),
        story_id=seed_story.id,
        name="Suite A",
        source_test_case_ids=[str(cases[0].id)],
        specs=[{"path": "tests/a.spec.ts", "content": "// stub"}],
    )
    db_session.add(artifact)
    await db_session.flush()

    response = await client.post(
        "/api/v1/executions/run",
        json={"automation_artifact_id": str(artifact.id)},
    )
    assert response.status_code == 201, response.text
    job = response.json()["job"]
    assert job["total"] == 1
    assert job["passed"] == 1
    assert job["status"] == AutomationStatus.COMPLETED.value
    assert job["config"]["automation_artifact_id"] == str(artifact.id)


@pytest.mark.asyncio
async def test_list_get_and_retry(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_story: Story,
    seed_project: Project,
):
    await _seed_approved_cases(db_session, seed_story)

    run = await client.post(
        "/api/v1/executions/run",
        json={"story_id": str(seed_story.id)},
    )
    assert run.status_code == 201
    job = run.json()["job"]
    failed = next(
        ex for ex in job["executions"] if ex["status"] == ExecutionStatus.FAILED.value
    )
    execution_id = failed["id"]

    listed = await client.get(
        "/api/v1/executions",
        params={"story_id": str(seed_story.id), "page_size": 10},
    )
    assert listed.status_code == 200
    assert listed.json()["total"] >= 2

    by_project = await client.get(
        "/api/v1/executions",
        params={"project_id": str(seed_project.id)},
    )
    assert by_project.status_code == 200
    assert by_project.json()["total"] >= 2

    detail = await client.get(f"/api/v1/executions/{execution_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == execution_id
    assert detail.json()["automation_job"]["id"] == job["id"]

    retried = await client.post(f"/api/v1/executions/{execution_id}/retry")
    assert retried.status_code == 200, retried.text
    body = retried.json()
    assert body["retry_count"] == 1
    # Title still contains "fail" → stub fails again
    assert body["status"] == ExecutionStatus.FAILED.value


@pytest.mark.asyncio
async def test_retry_rejects_passed_execution(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_story: Story,
):
    cases = await _seed_approved_cases(db_session, seed_story)
    run = await client.post(
        "/api/v1/executions/run",
        json={
            "story_id": str(seed_story.id),
            "force_fail_test_case_ids": [],
        },
    )
    # Still one title-based fail; find the passed one
    passed = next(
        ex
        for ex in run.json()["job"]["executions"]
        if ex["test_case_id"] == str(cases[0].id)
    )
    bad = await client.post(f"/api/v1/executions/{passed['id']}/retry")
    assert bad.status_code == 400


@pytest.mark.asyncio
async def test_run_requires_exactly_one_target(client: AsyncClient, seed_story: Story):
    response = await client.post(
        "/api/v1/executions/run",
        json={
            "story_id": str(seed_story.id),
            "automation_job_id": str(uuid4()),
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_run_by_job_id_and_workflow_events(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_story: Story,
):
    await _seed_approved_cases(db_session, seed_story)

    # First run creates a job
    first = await client.post(
        "/api/v1/executions/run",
        json={"story_id": str(seed_story.id)},
    )
    assert first.status_code == 201
    job_id = first.json()["job"]["id"]

    # Re-run via automation_job_id creates a new completed/failed job
    second = await client.post(
        "/api/v1/executions/run",
        json={"automation_job_id": job_id},
    )
    assert second.status_code == 201
    assert second.json()["job"]["id"] != job_id
    assert second.json()["job"]["total"] == 2

    # Advance a workflow to pull_request_created, then run with workflow_run_id
    start = await client.post(
        "/api/v1/workflows/start",
        json={"story_id": str(seed_story.id), "mark_synced": True},
    )
    run_id = start.json()["id"]
    # synced → analyzed → test_cases_generated
    for _ in range(2):
        adv = await client.post(f"/api/v1/workflows/{run_id}/advance")
        assert adv.status_code == 200
    approved = await client.post(
        f"/api/v1/workflows/{run_id}/approve",
        json={"approved": True},
    )
    assert approved.status_code == 200
    # qa_approved → bdd → automation → pr_created
    for _ in range(3):
        adv = await client.post(f"/api/v1/workflows/{run_id}/advance")
        assert adv.status_code == 200, adv.text
    assert adv.json()["state"] == WorkflowState.PR_CREATED.value

    with_wf = await client.post(
        "/api/v1/executions/run",
        json={
            "story_id": str(seed_story.id),
            "workflow_run_id": run_id,
        },
    )
    assert with_wf.status_code == 201, with_wf.text
    assert with_wf.json()["workflow_run_id"] == run_id

    status = await client.get(f"/api/v1/workflows/{run_id}")
    assert status.status_code == 200
    assert status.json()["state"] == WorkflowState.EXECUTION_COMPLETED.value
    assert status.json()["last_event"] == WorkflowEvent.EXECUTION_COMPLETED.value


@pytest.mark.asyncio
async def test_get_missing_execution(client: AsyncClient):
    response = await client.get(f"/api/v1/executions/{uuid4()}")
    assert response.status_code == 404

"""
API tests for Dashboard & Reporting endpoints.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automation_artifact import AutomationArtifact
from app.models.automation_job import AutomationJob
from app.models.bdd_feature import BddFeature
from app.models.enums import (
    AutomationStatus,
    ExecutionStatus,
    TestCaseSource,
    TestCaseStatus,
)
from app.models.execution import Execution
from app.models.organization import Organization
from app.models.project import Project
from app.models.sprint import Sprint
from app.models.story import Story
from app.models.story_analysis import StoryAnalysis
from app.models.test_case import TestCase


DASHBOARD_URL = "/api/v1/dashboard"


async def _seed_dashboard_data(
    db_session: AsyncSession,
    *,
    organization: Organization,
    project: Project,
) -> dict:
    sprint = Sprint(
        id=uuid4(),
        project_id=project.id,
        name="Sprint Dash",
        goal="Coverage",
    )
    story_with = Story(
        id=uuid4(),
        project_id=project.id,
        title="Covered story",
        external_id="DASH-1",
    )
    story_without = Story(
        id=uuid4(),
        project_id=project.id,
        title="Uncovered story",
        external_id="DASH-2",
    )
    db_session.add_all([sprint, story_with, story_without])
    await db_session.flush()

    analysis = StoryAnalysis(
        id=uuid4(),
        story_id=story_with.id,
        complexity="medium",
        risk="low",
        automation_candidate=True,
        summary="Ready for tests",
    )
    approved = TestCase(
        id=uuid4(),
        story_id=story_with.id,
        title="AI approved case",
        source=TestCaseSource.AI.value,
        status=TestCaseStatus.APPROVED.value,
        order_index=0,
    )
    draft = TestCase(
        id=uuid4(),
        story_id=story_with.id,
        title="Manual draft case",
        source=TestCaseSource.MANUAL.value,
        status=TestCaseStatus.DRAFT.value,
        order_index=1,
    )
    bdd = BddFeature(
        id=uuid4(),
        story_id=story_with.id,
        name="Login feature",
        gherkin_content="Feature: Login\n  Scenario: ok\n    Given x",
    )
    artifact = AutomationArtifact(
        id=uuid4(),
        story_id=story_with.id,
        name="login.spec.ts",
        language="typescript",
        framework="playwright",
    )
    db_session.add_all([analysis, approved, draft, bdd, artifact])
    await db_session.flush()

    job = AutomationJob(
        id=uuid4(),
        project_id=project.id,
        name="Dashboard stub run",
        status=AutomationStatus.COMPLETED,
    )
    db_session.add(job)
    await db_session.flush()

    now = datetime.now(timezone.utc)
    passed = Execution(
        id=uuid4(),
        automation_job_id=job.id,
        test_case_id=approved.id,
        status=ExecutionStatus.PASSED,
        created_at=now - timedelta(days=1),
    )
    failed = Execution(
        id=uuid4(),
        automation_job_id=job.id,
        test_case_id=draft.id,
        status=ExecutionStatus.FAILED,
        created_at=now - timedelta(hours=2),
    )
    db_session.add_all([passed, failed])
    await db_session.flush()

    return {
        "organization": organization,
        "project": project,
        "story_with": story_with,
        "story_without": story_without,
        "approved": approved,
        "draft": draft,
    }


@pytest.mark.asyncio
async def test_dashboard_summary(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_organization: Organization,
    seed_project: Project,
):
    await _seed_dashboard_data(
        db_session,
        organization=seed_organization,
        project=seed_project,
    )

    response = await client.get(
        f"{DASHBOARD_URL}/summary",
        params={"project_id": str(seed_project.id)},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["scope"]["project_id"] == str(seed_project.id)
    assert body["project_count"] == 1
    assert body["sprint_count"] >= 1
    assert body["story_count"] >= 2
    assert body["test_case_count"] >= 2
    assert body["execution_count"] >= 2
    assert body["automation_job_count"] >= 1
    assert body["executions_by_status"].get("passed", 0) >= 1
    assert body["executions_by_status"].get("failed", 0) >= 1


@pytest.mark.asyncio
async def test_dashboard_summary_org_scope(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_organization: Organization,
    seed_project: Project,
):
    await _seed_dashboard_data(
        db_session,
        organization=seed_organization,
        project=seed_project,
    )
    response = await client.get(
        f"{DASHBOARD_URL}/summary",
        params={"organization_id": str(seed_organization.id)},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["scope"]["organization_id"] == str(seed_organization.id)
    assert body["project_count"] >= 1


@pytest.mark.asyncio
async def test_dashboard_summary_project_not_found(client: AsyncClient):
    response = await client.get(
        f"{DASHBOARD_URL}/summary",
        params={"project_id": str(uuid4())},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_dashboard_summary_org_project_mismatch(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_organization: Organization,
    seed_project: Project,
):
    other_org = Organization(
        id=uuid4(),
        name="Other Org",
        slug=f"other-{uuid4().hex[:8]}",
    )
    db_session.add(other_org)
    await db_session.flush()

    response = await client.get(
        f"{DASHBOARD_URL}/summary",
        params={
            "organization_id": str(other_org.id),
            "project_id": str(seed_project.id),
        },
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_execution_trends(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_organization: Organization,
    seed_project: Project,
):
    await _seed_dashboard_data(
        db_session,
        organization=seed_organization,
        project=seed_project,
    )
    response = await client.get(
        f"{DASHBOARD_URL}/execution-trends",
        params={
            "project_id": str(seed_project.id),
            "days": 7,
            "bucket": "day",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["days"] == 7
    assert body["bucket"] == "day"
    assert len(body["buckets"]) == 7
    total = sum(b["total"] for b in body["buckets"])
    assert total >= 2
    assert sum(b["passed"] for b in body["buckets"]) >= 1
    assert sum(b["failed"] for b in body["buckets"]) >= 1


@pytest.mark.asyncio
async def test_execution_trends_invalid_bucket(
    client: AsyncClient,
    seed_project: Project,
):
    response = await client.get(
        f"{DASHBOARD_URL}/execution-trends",
        params={"project_id": str(seed_project.id), "bucket": "month"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_coverage(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_organization: Organization,
    seed_project: Project,
):
    await _seed_dashboard_data(
        db_session,
        organization=seed_organization,
        project=seed_project,
    )
    response = await client.get(
        f"{DASHBOARD_URL}/coverage",
        params={"project_id": str(seed_project.id)},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["stories_total"] >= 2
    assert body["stories_with_test_cases"] >= 1
    assert body["stories_without_test_cases"] >= 1
    assert body["test_cases_total"] >= 2
    assert body["test_cases_approved"] >= 1
    assert body["test_cases_draft"] >= 1
    assert 0.0 <= body["approved_ratio"] <= 1.0
    assert 0.0 <= body["coverage_ratio"] <= 1.0


@pytest.mark.asyncio
async def test_ai_metrics(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_organization: Organization,
    seed_project: Project,
):
    await _seed_dashboard_data(
        db_session,
        organization=seed_organization,
        project=seed_project,
    )
    response = await client.get(
        f"{DASHBOARD_URL}/ai-metrics",
        params={"project_id": str(seed_project.id)},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["analyses_count"] >= 1
    assert body["generated_test_cases"] >= 1
    assert body["bdd_artifacts"] >= 1
    assert body["playwright_artifacts"] >= 1


@pytest.mark.asyncio
async def test_dashboard_empty_scope(client: AsyncClient):
    """Platform-wide empty DB still returns zeroed payloads."""
    response = await client.get(f"{DASHBOARD_URL}/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["project_count"] == 0
    assert body["story_count"] == 0

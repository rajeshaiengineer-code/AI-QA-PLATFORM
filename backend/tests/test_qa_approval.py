"""
Unit / API tests for QA Approval (test case review).
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Priority, TestCaseSource, TestCaseStatus
from app.models.project import Project
from app.models.story import Story
from app.models.test_case import TestCase
from app.orchestration.state.enums import WorkflowState


STORIES_URL = "/api/v1/stories"
TEST_CASES_URL = "/api/v1/test-cases"
WORKFLOWS_URL = "/api/v1/workflows"


async def _seed_test_case(
    db_session: AsyncSession,
    story: Story,
    *,
    title: str = "Sample test",
    status: str = TestCaseStatus.PENDING_REVIEW.value,
    order_index: int = 0,
) -> TestCase:
    entity = TestCase(
        id=uuid4(),
        story_id=story.id,
        title=title,
        description="Desc",
        preconditions="Pre",
        steps=[{"action": "Do thing", "expected": "OK"}],
        expected_result="Pass",
        priority=Priority.MEDIUM,
        is_automated=False,
        order_index=order_index,
        category="positive",
        source=TestCaseSource.AI.value,
        status=status,
        tags=["positive"],
    )
    db_session.add(entity)
    await db_session.flush()
    return entity


@pytest.mark.asyncio
async def test_list_pending_review(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_story: Story,
):
    pending = await _seed_test_case(db_session, seed_story, title="Pending A")
    await _seed_test_case(
        db_session,
        seed_story,
        title="Already approved",
        status=TestCaseStatus.APPROVED.value,
        order_index=1,
    )

    response = await client.get(
        f"{STORIES_URL}/{seed_story.id}/test-cases",
        params={"status": "pending_review"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == str(pending.id)
    assert body["items"][0]["status"] == "pending_review"


@pytest.mark.asyncio
async def test_get_and_update_test_case_creates_version(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_story: Story,
):
    tc = await _seed_test_case(db_session, seed_story)

    get_resp = await client.get(f"{TEST_CASES_URL}/{tc.id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["title"] == "Sample test"

    put_resp = await client.put(
        f"{TEST_CASES_URL}/{tc.id}",
        json={
            "title": "Updated title",
            "expected_result": "New expected",
            "change_reason": "Clarify assertion",
            "steps": [
                {"action": "Open page", "expected": "Loads"},
                {"action": "Click submit", "expected": "Success"},
            ],
        },
    )
    assert put_resp.status_code == 200
    updated = put_resp.json()
    assert updated["title"] == "Updated title"
    assert updated["expected_result"] == "New expected"
    assert len(updated["steps"]) == 2
    assert updated["status"] == "pending_review"

    versions = await client.get(f"{TEST_CASES_URL}/{tc.id}/versions")
    assert versions.status_code == 200
    vbody = versions.json()
    assert vbody["total"] == 1
    assert vbody["items"][0]["title"] == "Sample test"
    assert vbody["items"][0]["change_reason"] == "Clarify assertion"
    assert vbody["items"][0]["version_number"] == 1


@pytest.mark.asyncio
async def test_edit_approved_resets_to_pending_review(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_story: Story,
):
    tc = await _seed_test_case(
        db_session,
        seed_story,
        status=TestCaseStatus.APPROVED.value,
    )
    resp = await client.put(
        f"{TEST_CASES_URL}/{tc.id}",
        json={"title": "Rework after approval"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "pending_review"


@pytest.mark.asyncio
async def test_approve_and_reject_individual(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_story: Story,
):
    a = await _seed_test_case(db_session, seed_story, title="Case A", order_index=0)
    b = await _seed_test_case(db_session, seed_story, title="Case B", order_index=1)

    approve = await client.post(f"{TEST_CASES_URL}/{a.id}/approve", json={})
    assert approve.status_code == 200
    body = approve.json()
    assert body["test_case"]["status"] == "approved"
    assert body["workflow_advanced"] is False
    assert "awaiting approval" in (body["message"] or "")

    reject = await client.post(
        f"{TEST_CASES_URL}/{b.id}/reject",
        json={"reason": "Steps incomplete"},
    )
    assert reject.status_code == 200
    rbody = reject.json()
    assert rbody["test_case"]["status"] == "rejected"
    assert rbody["test_case"]["rejection_reason"] == "Steps incomplete"


@pytest.mark.asyncio
async def test_approve_all_advances_workflow(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_project: Project,
    seed_story: Story,
):
    await _seed_test_case(db_session, seed_story, title="TC1", order_index=0)
    await _seed_test_case(db_session, seed_story, title="TC2", order_index=1)

    start = await client.post(
        f"{WORKFLOWS_URL}/start",
        json={
            "story_id": str(seed_story.id),
            "mark_synced": True,
            "max_retries": 3,
        },
    )
    assert start.status_code == 201
    run_id = start.json()["id"]

    # Advance through analyzed → test_cases_generated (no agents registered).
    adv1 = await client.post(f"{WORKFLOWS_URL}/{run_id}/advance")
    assert adv1.status_code == 200
    assert adv1.json()["state"] == WorkflowState.ANALYZED.value

    adv2 = await client.post(f"{WORKFLOWS_URL}/{run_id}/advance")
    assert adv2.status_code == 200
    assert adv2.json()["state"] == WorkflowState.TEST_CASES_GENERATED.value

    result = await client.post(
        f"{STORIES_URL}/{seed_story.id}/test-cases/approve-all",
    )
    assert result.status_code == 200
    body = result.json()
    assert body["approved_count"] == 2
    assert body["workflow_advanced"] is True
    assert body["workflow_run_id"] == run_id

    status = await client.get(f"{WORKFLOWS_URL}/{run_id}")
    assert status.status_code == 200
    assert status.json()["state"] == WorkflowState.QA_APPROVED.value


@pytest.mark.asyncio
async def test_last_individual_approve_advances_workflow(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_story: Story,
):
    a = await _seed_test_case(db_session, seed_story, title="Only one")

    start = await client.post(
        f"{WORKFLOWS_URL}/start",
        json={"story_id": str(seed_story.id), "mark_synced": True},
    )
    run_id = start.json()["id"]
    await client.post(f"{WORKFLOWS_URL}/{run_id}/advance")
    await client.post(f"{WORKFLOWS_URL}/{run_id}/advance")

    approve = await client.post(f"{TEST_CASES_URL}/{a.id}/approve", json={})
    assert approve.status_code == 200
    assert approve.json()["workflow_advanced"] is True

    status = await client.get(f"{WORKFLOWS_URL}/{run_id}")
    assert status.json()["state"] == WorkflowState.QA_APPROVED.value


@pytest.mark.asyncio
async def test_approve_all_without_workflow(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_story: Story,
):
    await _seed_test_case(db_session, seed_story)
    result = await client.post(
        f"{STORIES_URL}/{seed_story.id}/test-cases/approve-all",
    )
    assert result.status_code == 200
    body = result.json()
    assert body["approved_count"] == 1
    assert body["workflow_advanced"] is False
    assert "no workflow run" in (body["message"] or "").lower()


@pytest.mark.asyncio
async def test_not_found_and_double_approve(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_story: Story,
):
    missing = uuid4()
    assert (await client.get(f"{TEST_CASES_URL}/{missing}")).status_code == 404

    tc = await _seed_test_case(db_session, seed_story)
    first = await client.post(f"{TEST_CASES_URL}/{tc.id}/approve", json={})
    assert first.status_code == 200
    second = await client.post(f"{TEST_CASES_URL}/{tc.id}/approve", json={})
    assert second.status_code == 400

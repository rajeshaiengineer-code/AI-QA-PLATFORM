"""
Tests for Workflow Engine — transitions, persistence, API.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.project import Project
from app.models.story import Story
from app.orchestration.events.enums import WorkflowEvent
from app.orchestration.state.enums import WorkflowState
from app.orchestration.state.transitions import TransitionError, transition_for


class TestTransitions:
    def test_happy_path_import(self):
        assert (
            transition_for(WorkflowState.NEW, WorkflowEvent.STORY_IMPORTED)
            == WorkflowState.SYNCED
        )

    def test_qa_approve(self):
        assert (
            transition_for(
                WorkflowState.TEST_CASES_GENERATED,
                WorkflowEvent.STORY_APPROVED,
            )
            == WorkflowState.QA_APPROVED
        )

    def test_invalid_transition(self):
        with pytest.raises(TransitionError):
            transition_for(WorkflowState.NEW, WorkflowEvent.STORY_ANALYZED)

    def test_terminal_reject(self):
        with pytest.raises(TransitionError):
            transition_for(WorkflowState.COMPLETED, WorkflowEvent.STORY_IMPORTED)


@pytest.mark.asyncio
async def test_start_and_advance_workflow(
    client: AsyncClient,
    seed_story: Story,
):
    start = await client.post(
        "/api/v1/workflows/start",
        json={"story_id": str(seed_story.id), "mark_synced": True},
    )
    assert start.status_code == 201
    body = start.json()
    assert body["state"] == "synced"
    assert body["story_id"] == str(seed_story.id)
    assert len(body["logs"]) >= 1
    run_id = body["id"]

    # Advance SYNCED → ANALYZED
    adv = await client.post(f"/api/v1/workflows/{run_id}/advance")
    assert adv.status_code == 200
    assert adv.json()["state"] == "analyzed"

    # Advance ANALYZED → TEST_CASES_GENERATED
    adv2 = await client.post(f"/api/v1/workflows/{run_id}/advance")
    assert adv2.status_code == 200
    assert adv2.json()["state"] == "test_cases_generated"

    # QA gate blocks advance
    blocked = await client.post(f"/api/v1/workflows/{run_id}/advance")
    assert blocked.status_code == 400

    approved = await client.post(
        f"/api/v1/workflows/{run_id}/approve",
        json={"approved": True},
    )
    assert approved.status_code == 200
    assert approved.json()["state"] == "qa_approved"

    by_story = await client.get(f"/api/v1/workflows/by-story/{seed_story.id}")
    assert by_story.status_code == 200
    assert by_story.json()["id"] == run_id


@pytest.mark.asyncio
async def test_cancel_workflow(client: AsyncClient, seed_story: Story):
    start = await client.post(
        "/api/v1/workflows/start",
        json={"story_id": str(seed_story.id)},
    )
    run_id = start.json()["id"]

    cancelled = await client.post(
        f"/api/v1/workflows/{run_id}/cancel",
        json={"reason": "No longer needed"},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["state"] == "cancelled"


@pytest.mark.asyncio
async def test_retry_workflow(client: AsyncClient, seed_story: Story):
    start = await client.post(
        "/api/v1/workflows/start",
        json={"story_id": str(seed_story.id)},
    )
    run_id = start.json()["id"]
    await client.post(f"/api/v1/workflows/{run_id}/advance")

    retried = await client.post(
        f"/api/v1/workflows/{run_id}/retry",
        json={"from_state": "synced"},
    )
    assert retried.status_code == 200
    assert retried.json()["state"] == "synced"
    assert retried.json()["retry_count"] == 0


@pytest.mark.asyncio
async def test_start_missing_story(client: AsyncClient):
    response = await client.post(
        "/api/v1/workflows/start",
        json={"story_id": str(uuid4())},
    )
    assert response.status_code == 404

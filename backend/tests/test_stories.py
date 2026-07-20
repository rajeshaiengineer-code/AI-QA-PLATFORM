"""
Unit / API tests for Story CRUD endpoints.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.enums import Priority, StoryStatus, StoryType
from app.models.project import Project
from app.models.sprint import Sprint


STORIES_URL = "/api/v1/stories"


def _story_payload(project_id, **overrides):
    data = {
        "project_id": str(project_id),
        "title": "User can reset password",
        "description": "As a user I want to reset my password.",
        "status": StoryStatus.DRAFT.value,
        "story_type": StoryType.FEATURE.value,
        "priority": Priority.MEDIUM.value,
        "story_points": 3,
        "external_id": "TST-101",
        "rank": 1,
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_create_story(client: AsyncClient, seed_project: Project):
    response = await client.post(STORIES_URL, json=_story_payload(seed_project.id))
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "User can reset password"
    assert body["project_id"] == str(seed_project.id)
    assert body["status"] == "draft"
    assert body["external_id"] == "TST-101"
    assert body["version"] == 1
    assert body["is_deleted"] is False
    assert "id" in body


@pytest.mark.asyncio
async def test_create_story_invalid_project(client: AsyncClient):
    response = await client.post(STORIES_URL, json=_story_payload(uuid4()))
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"


@pytest.mark.asyncio
async def test_create_story_validation_error(client: AsyncClient, seed_project: Project):
    payload = _story_payload(seed_project.id, title="")
    response = await client.post(STORIES_URL, json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_get_story(client: AsyncClient, seed_project: Project):
    created = await client.post(STORIES_URL, json=_story_payload(seed_project.id))
    story_id = created.json()["id"]

    response = await client.get(f"{STORIES_URL}/{story_id}")
    assert response.status_code == 200
    assert response.json()["id"] == story_id


@pytest.mark.asyncio
async def test_get_story_not_found(client: AsyncClient):
    response = await client.get(f"{STORIES_URL}/{uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_list_stories_pagination(client: AsyncClient, seed_project: Project):
    for i in range(3):
        await client.post(
            STORIES_URL,
            json=_story_payload(
                seed_project.id,
                title=f"Story {i}",
                external_id=f"TST-{i}",
            ),
        )

    response = await client.get(STORIES_URL, params={"page": 1, "page_size": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert body["total_pages"] == 2
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_list_stories_filters(
    client: AsyncClient,
    seed_project: Project,
    seed_sprint: Sprint,
):
    await client.post(
        STORIES_URL,
        json=_story_payload(
            seed_project.id,
            title="High priority feature",
            status=StoryStatus.READY.value,
            story_type=StoryType.FEATURE.value,
            priority=Priority.HIGH.value,
            sprint_id=str(seed_sprint.id),
            external_id="TST-HIGH",
        ),
    )
    await client.post(
        STORIES_URL,
        json=_story_payload(
            seed_project.id,
            title="Low priority bug",
            status=StoryStatus.DRAFT.value,
            story_type=StoryType.BUG.value,
            priority=Priority.LOW.value,
            external_id="TST-LOW",
        ),
    )

    response = await client.get(
        STORIES_URL,
        params={
            "status": "ready",
            "story_type": "feature",
            "priority": "high",
            "sprint_id": str(seed_sprint.id),
            "project_id": str(seed_project.id),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["external_id"] == "TST-HIGH"


@pytest.mark.asyncio
async def test_list_stories_search_by_title_and_key(
    client: AsyncClient,
    seed_project: Project,
):
    await client.post(
        STORIES_URL,
        json=_story_payload(
            seed_project.id,
            title="Reset password flow",
            external_id="AUTH-42",
        ),
    )
    await client.post(
        STORIES_URL,
        json=_story_payload(
            seed_project.id,
            title="Unrelated story",
            external_id="OTHER-1",
        ),
    )

    by_title = await client.get(STORIES_URL, params={"search": "password"})
    assert by_title.status_code == 200
    assert by_title.json()["total"] == 1
    assert by_title.json()["items"][0]["external_id"] == "AUTH-42"

    by_key = await client.get(STORIES_URL, params={"search": "AUTH-42"})
    assert by_key.status_code == 200
    assert by_key.json()["total"] == 1
    assert by_key.json()["items"][0]["title"] == "Reset password flow"


@pytest.mark.asyncio
async def test_update_story(client: AsyncClient, seed_project: Project):
    created = await client.post(STORIES_URL, json=_story_payload(seed_project.id))
    story_id = created.json()["id"]

    response = await client.put(
        f"{STORIES_URL}/{story_id}",
        json={
            "title": "Updated title",
            "status": StoryStatus.IN_PROGRESS.value,
            "priority": Priority.CRITICAL.value,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Updated title"
    assert body["status"] == "in_progress"
    assert body["priority"] == "critical"
    assert body["version"] >= 1


@pytest.mark.asyncio
async def test_update_story_not_found(client: AsyncClient):
    response = await client.put(
        f"{STORIES_URL}/{uuid4()}",
        json={"title": "Nope"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_story(client: AsyncClient, seed_project: Project):
    created = await client.post(STORIES_URL, json=_story_payload(seed_project.id))
    story_id = created.json()["id"]

    delete_response = await client.delete(f"{STORIES_URL}/{story_id}")
    assert delete_response.status_code == 200
    assert delete_response.json()["success"] is True

    get_response = await client.get(f"{STORIES_URL}/{story_id}")
    assert get_response.status_code == 404

    list_response = await client.get(STORIES_URL)
    assert list_response.json()["total"] == 0


@pytest.mark.asyncio
async def test_create_story_sprint_project_mismatch(
    client: AsyncClient,
    seed_project: Project,
    db_session,
):
    """Sprint belonging to another project should be rejected."""
    from app.models.organization import Organization
    from app.models.project import Project as ProjectModel
    from app.models.sprint import Sprint as SprintModel

    other_org = Organization(
        id=uuid4(),
        name="Other Org",
        slug=f"other-{uuid4().hex[:8]}",
    )
    other_project = ProjectModel(
        id=uuid4(),
        organization_id=other_org.id,
        name="Other",
        key="OTH",
    )
    other_sprint = SprintModel(
        id=uuid4(),
        project_id=other_project.id,
        name="Other Sprint",
    )
    db_session.add_all([other_org, other_project, other_sprint])
    await db_session.flush()

    response = await client.post(
        STORIES_URL,
        json=_story_payload(
            seed_project.id,
            sprint_id=str(other_sprint.id),
        ),
    )
    assert response.status_code == 400
    assert "does not belong" in response.json()["error"]["message"]


@pytest.mark.asyncio
async def test_openapi_includes_stories(client: AsyncClient):
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    paths = schema["paths"]
    assert "/api/v1/stories" in paths
    assert "/api/v1/stories/{story_id}" in paths
    assert "Stories" in [tag["name"] for tag in schema.get("tags", [])] or any(
        "Stories" in (op.get("tags") or [])
        for methods in paths.values()
        for op in methods.values()
        if isinstance(op, dict)
    )

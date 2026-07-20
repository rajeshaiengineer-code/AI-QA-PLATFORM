"""
API tests for Sprint CRUD endpoints.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.project import Project
from app.models.sprint import Sprint


SPRINTS_URL = "/api/v1/sprints"


def _sprint_payload(project_id, **overrides):
    data = {
        "project_id": str(project_id),
        "name": "Sprint 14",
        "goal": "Ship checkout hardening",
        "start_date": "2026-07-01",
        "end_date": "2026-07-14",
        "is_active": True,
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_create_sprint(client: AsyncClient, seed_project: Project):
    response = await client.post(
        SPRINTS_URL,
        json=_sprint_payload(seed_project.id),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Sprint 14"
    assert body["project_id"] == str(seed_project.id)
    assert body["is_deleted"] is False


@pytest.mark.asyncio
async def test_create_sprint_invalid_project(client: AsyncClient):
    response = await client.post(SPRINTS_URL, json=_sprint_payload(uuid4()))
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_sprint_invalid_dates(
    client: AsyncClient,
    seed_project: Project,
):
    response = await client.post(
        SPRINTS_URL,
        json=_sprint_payload(
            seed_project.id,
            start_date="2026-07-14",
            end_date="2026-07-01",
        ),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_sprints(client: AsyncClient, seed_sprint: Sprint):
    response = await client.get(
        SPRINTS_URL,
        params={"project_id": str(seed_sprint.project_id)},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert any(item["id"] == str(seed_sprint.id) for item in body["items"])


@pytest.mark.asyncio
async def test_get_sprint(client: AsyncClient, seed_sprint: Sprint):
    response = await client.get(f"{SPRINTS_URL}/{seed_sprint.id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(seed_sprint.id)


@pytest.mark.asyncio
async def test_update_sprint(client: AsyncClient, seed_sprint: Sprint):
    response = await client.put(
        f"{SPRINTS_URL}/{seed_sprint.id}",
        json={"name": "Sprint 14b", "goal": "Updated goal"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Sprint 14b"
    assert body["goal"] == "Updated goal"


@pytest.mark.asyncio
async def test_delete_sprint(client: AsyncClient, seed_project: Project):
    created = await client.post(
        SPRINTS_URL,
        json=_sprint_payload(seed_project.id, name="Temp Sprint"),
    )
    sprint_id = created.json()["id"]

    response = await client.delete(f"{SPRINTS_URL}/{sprint_id}")
    assert response.status_code == 200

    get_response = await client.get(f"{SPRINTS_URL}/{sprint_id}")
    assert get_response.status_code == 404

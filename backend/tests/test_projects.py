"""
API tests for Project CRUD and dashboard endpoints.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from app.models.organization import Organization
from app.models.project import Project


PROJECTS_URL = "/api/v1/projects"


def _project_payload(organization_id, **overrides):
    data = {
        "organization_id": str(organization_id),
        "name": "Payments Platform",
        "key": "PAY",
        "description": "Core payment rails",
        "is_active": True,
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, seed_organization: Organization):
    response = await client.post(
        PROJECTS_URL,
        json=_project_payload(seed_organization.id, key="NEW"),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Payments Platform"
    assert body["key"] == "NEW"
    assert body["organization_id"] == str(seed_organization.id)
    assert body["is_deleted"] is False


@pytest.mark.asyncio
async def test_create_project_invalid_org(client: AsyncClient):
    response = await client.post(PROJECTS_URL, json=_project_payload(uuid4()))
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"


@pytest.mark.asyncio
async def test_create_project_duplicate_key(
    client: AsyncClient,
    seed_project: Project,
):
    response = await client.post(
        PROJECTS_URL,
        json=_project_payload(seed_project.organization_id, key=seed_project.key),
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient, seed_project: Project):
    response = await client.get(PROJECTS_URL)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert any(item["id"] == str(seed_project.id) for item in body["items"])


@pytest.mark.asyncio
async def test_list_projects_search(client: AsyncClient, seed_project: Project):
    response = await client.get(PROJECTS_URL, params={"search": seed_project.key})
    assert response.status_code == 200
    assert response.json()["total"] >= 1


@pytest.mark.asyncio
async def test_get_project(client: AsyncClient, seed_project: Project):
    response = await client.get(f"{PROJECTS_URL}/{seed_project.id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(seed_project.id)


@pytest.mark.asyncio
async def test_get_project_not_found(client: AsyncClient):
    response = await client.get(f"{PROJECTS_URL}/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_project(client: AsyncClient, seed_project: Project):
    response = await client.put(
        f"{PROJECTS_URL}/{seed_project.id}",
        json={"name": "Updated Name", "description": "Updated"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Updated Name"
    assert body["description"] == "Updated"


@pytest.mark.asyncio
async def test_project_dashboard(client: AsyncClient, seed_project: Project):
    response = await client.get(f"{PROJECTS_URL}/{seed_project.id}/dashboard")
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == str(seed_project.id)
    assert "story_total" in body
    assert "sprint_total" in body
    assert "story_by_status" in body


@pytest.mark.asyncio
async def test_delete_project(client: AsyncClient, seed_organization: Organization):
    created = await client.post(
        PROJECTS_URL,
        json=_project_payload(seed_organization.id, key="DEL"),
    )
    project_id = created.json()["id"]

    response = await client.delete(f"{PROJECTS_URL}/{project_id}")
    assert response.status_code == 200
    assert response.json()["success"] is True

    get_response = await client.get(f"{PROJECTS_URL}/{project_id}")
    assert get_response.status_code == 404

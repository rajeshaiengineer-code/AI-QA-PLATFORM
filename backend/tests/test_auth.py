"""
Authentication + RBAC unit / API tests.

AUTH_ENABLED defaults to False so existing suite stays green.
These tests cover auth flows and optional enforcement when enabled.
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    TOKEN_TYPE_ACCESS,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import OrganizationRole
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.models.user import User


@pytest.fixture(autouse=True)
def _reset_auth_settings():
    """Ensure AUTH_ENABLED stays False unless a test enables it."""
    get_settings.cache_clear()
    settings = get_settings()
    settings.AUTH_ENABLED = False
    yield
    settings.AUTH_ENABLED = False
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_password_hash_roundtrip():
    hashed = hash_password("SecretPass1!")
    assert hashed != "SecretPass1!"
    assert verify_password("SecretPass1!", hashed) is True
    assert verify_password("wrong", hashed) is False


@pytest.mark.asyncio
async def test_jwt_access_and_refresh_types():
    user_id = uuid4()
    access = create_access_token(user_id)
    refresh = create_refresh_token(user_id)
    access_payload = decode_token(access, expected_type=TOKEN_TYPE_ACCESS)
    refresh_payload = decode_token(refresh, expected_type="refresh")
    assert access_payload["sub"] == str(user_id)
    assert refresh_payload["sub"] == str(user_id)
    assert access_payload["type"] == "access"
    assert refresh_payload["type"] == "refresh"


@pytest.mark.asyncio
async def test_register_login_me_refresh(client: AsyncClient):
    email = f"qa-{uuid4().hex[:8]}@example.com"
    register = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecretPass1!",
            "full_name": "QA User",
            "organization_name": "Auth Org",
            "organization_slug": f"auth-org-{uuid4().hex[:6]}",
        },
    )
    assert register.status_code == 201, register.text
    body = register.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["user"]["email"] == email
    assert len(body["user"]["memberships"]) == 1
    assert body["user"]["memberships"][0]["role"] == "admin"

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecretPass1!"},
    )
    assert login.status_code == 200, login.text
    tokens = login.json()

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200, me.text
    assert me.json()["email"] == email
    assert me.json()["full_name"] == "QA User"

    refreshed = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["access_token"]
    assert refreshed.json()["user"]["email"] == email


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    email = f"dup-{uuid4().hex[:8]}@example.com"
    payload = {
        "email": email,
        "password": "SecretPass1!",
        "full_name": "Dup User",
    }
    first = await client.post("/api/v1/auth/register", json=payload)
    assert first.status_code == 201
    second = await client.post("/api/v1/auth/register", json=payload)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    email = f"bad-{uuid4().hex[:8]}@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecretPass1!",
            "full_name": "Bad Login",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "wrong-password"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rejects_access_token(client: AsyncClient):
    email = f"tok-{uuid4().hex[:8]}@example.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecretPass1!",
            "full_name": "Token User",
        },
    )
    access = reg.json()["access_token"]
    resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_join_existing_organization(
    client: AsyncClient,
    seed_organization: Organization,
):
    email = f"join-{uuid4().hex[:8]}@example.com"
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SecretPass1!",
            "full_name": "Joiner",
            "organization_id": str(seed_organization.id),
        },
    )
    assert resp.status_code == 201, resp.text
    memberships = resp.json()["user"]["memberships"]
    assert len(memberships) == 1
    assert memberships[0]["organization_id"] == str(seed_organization.id)
    assert memberships[0]["role"] == "viewer"


@pytest.mark.asyncio
async def test_auth_disabled_allows_story_write_without_token(
    client: AsyncClient,
    seed_project,
):
    """Default AUTH_ENABLED=False keeps write ops open."""
    resp = await client.post(
        "/api/v1/stories",
        json={
            "project_id": str(seed_project.id),
            "title": "Open write story",
            "description": "No auth required",
        },
    )
    assert resp.status_code == 201, resp.text


@pytest.mark.asyncio
async def test_auth_enabled_requires_token_for_story_write(
    client: AsyncClient,
    seed_project,
):
    settings = get_settings()
    settings.AUTH_ENABLED = True
    try:
        denied = await client.post(
            "/api/v1/stories",
            json={
                "project_id": str(seed_project.id),
                "title": "Denied story",
                "description": "Needs JWT",
            },
        )
        assert denied.status_code == 401

        email = f"writer-{uuid4().hex[:8]}@example.com"
        reg = await client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "SecretPass1!",
                "full_name": "Writer",
                "organization_name": f"Write Org {uuid4().hex[:4]}",
                "organization_slug": f"write-org-{uuid4().hex[:6]}",
            },
        )
        assert reg.status_code == 201, reg.text
        token = reg.json()["access_token"]

        allowed = await client.post(
            "/api/v1/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "project_id": str(seed_project.id),
                "title": "Authed story",
                "description": "JWT present",
            },
        )
        assert allowed.status_code == 201, allowed.text
    finally:
        settings.AUTH_ENABLED = False


@pytest.mark.asyncio
async def test_auth_enabled_viewer_cannot_write(
    client: AsyncClient,
    db_session: AsyncSession,
    seed_organization: Organization,
    seed_project,
):
    settings = get_settings()
    settings.AUTH_ENABLED = True
    try:
        user = User(
            email=f"viewer-{uuid4().hex[:8]}@example.com",
            hashed_password=hash_password("SecretPass1!"),
            full_name="Viewer Only",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()
        membership = OrganizationMembership(
            user_id=user.id,
            organization_id=seed_organization.id,
            role=OrganizationRole.VIEWER.value,
        )
        db_session.add(membership)
        await db_session.commit()

        token = create_access_token(user.id)
        resp = await client.post(
            "/api/v1/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "project_id": str(seed_project.id),
                "title": "Viewer blocked",
                "description": "Should 403",
            },
        )
        assert resp.status_code == 403
    finally:
        settings.AUTH_ENABLED = False

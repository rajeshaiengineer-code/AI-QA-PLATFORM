"""
Pytest Configuration and Fixtures

Provides shared fixtures for testing.
Uses an in-memory SQLite database with only Story-related tables
(avoids PostgreSQL-specific types such as JSONB).
"""

import asyncio
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.dependencies import get_db
from app.main import app
from app.models import (
    AcceptanceCriteria,
    AutomationArtifact,
    AutomationJob,
    BddFeature,
    Bug,
    Execution,
    FailureAnalysis,
    NotificationLog,
    Organization,
    OrganizationMembership,
    Project,
    Sprint,
    Story,
    StoryAnalysis,
    TestCase,
    TestCaseVersion,
    User,
    WorkflowLog,
    WorkflowRun,
)


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Tables required for Story / Project / Sprint / Workflow / Analysis / TestCase /
# BDD / Playwright / Execution / FailureAnalysis / Bug / Auth / Notifications tests.
STORY_TEST_TABLES = [
    Organization.__table__,
    User.__table__,
    OrganizationMembership.__table__,
    Project.__table__,
    Sprint.__table__,
    Story.__table__,
    AcceptanceCriteria.__table__,
    StoryAnalysis.__table__,
    TestCase.__table__,
    TestCaseVersion.__table__,
    BddFeature.__table__,
    AutomationArtifact.__table__,
    AutomationJob.__table__,
    Execution.__table__,
    FailureAnalysis.__table__,
    Bug.__table__,
    NotificationLog.__table__,
    WorkflowRun.__table__,
    WorkflowLog.__table__,
]


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create database session for tests."""
    async with test_engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(sync_conn, tables=STORY_TEST_TABLES)
        )

    async with TestSessionLocal() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.drop_all(sync_conn, tables=STORY_TEST_TABLES)
        )


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client with DB dependency override."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Lifespan may register workflow agents; clear so engine tests use auto
    # transitions unless a test explicitly re-registers them.
    from app.orchestration.runtime import get_agent_registry

    get_agent_registry().clear()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
    get_agent_registry().clear()


@pytest_asyncio.fixture
async def seed_organization(db_session: AsyncSession) -> Organization:
    """Create an organization for project tests."""
    org = Organization(
        id=uuid4(),
        name="Test Org",
        slug=f"test-org-{uuid4().hex[:8]}",
        description="Test organization",
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest_asyncio.fixture
async def seed_project(
    db_session: AsyncSession,
    seed_organization: Organization,
) -> Project:
    """Create a project under the seeded organization."""
    project = Project(
        id=uuid4(),
        organization_id=seed_organization.id,
        name="Test Project",
        key="TST",
        description="Test project",
    )
    db_session.add(project)
    await db_session.flush()
    return project


@pytest_asyncio.fixture
async def seed_sprint(db_session: AsyncSession, seed_project: Project) -> Sprint:
    """Create a sprint under the seeded project."""
    sprint = Sprint(
        id=uuid4(),
        project_id=seed_project.id,
        name="Sprint 1",
        goal="Ship story CRUD",
    )
    db_session.add(sprint)
    await db_session.flush()
    return sprint


@pytest_asyncio.fixture
async def seed_story(db_session: AsyncSession, seed_project: Project) -> Story:
    """Create a story under the seeded project."""
    story = Story(
        id=uuid4(),
        project_id=seed_project.id,
        title="Workflow test story",
        description="Used by workflow engine tests",
        external_id="WF-1",
    )
    db_session.add(story)
    await db_session.flush()
    return story


@pytest.fixture(scope="function")
def sync_client() -> Generator[TestClient, None, None]:
    """Create sync HTTP client for simple tests."""
    with TestClient(app) as client:
        yield client

"""
Story API Endpoints

CRUD operations for Story management.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import PaginationParams, get_db, get_pagination
from app.core.exceptions import ErrorResponse
from app.core.rbac import require_write_access
from app.models.enums import Priority, StoryStatus, StoryType, TestCaseCategory, TestCaseSource, TestCaseStatus
from app.models.user import User
from app.schemas.base import MessageResponse
from app.schemas.bdd_feature import (
    BddFeatureListResponse,
    BddGenerateRequest,
    BddGenerateResponse,
)
from app.schemas.automation_artifact import (
    AutomationArtifactListResponse,
    PlaywrightGenerateRequest,
    PlaywrightGenerateResponse,
)
from app.schemas.story import (
    StoryCreate,
    StoryListResponse,
    StoryResponse,
    StoryUpdate,
)
from app.schemas.story_analysis import (
    StoryAnalysisResponse,
    StoryAnalyzeRequest,
)
from app.schemas.test_case import (
    TestCaseApproveAllResponse,
    TestCaseGenerateRequest,
    TestCaseGenerateResponse,
    TestCaseListResponse,
)
from app.services.bdd_generator import BddGeneratorService
from app.services.playwright_generator import PlaywrightGeneratorService
from app.services.qa_approval import QAApprovalService
from app.services.story import StoryService
from app.services.story_analyzer import StoryAnalyzerService
from app.services.test_case_generator import TestCaseGeneratorService

router = APIRouter()


def get_story_service(db: AsyncSession = Depends(get_db)) -> StoryService:
    """Dependency that builds a StoryService for the request session."""
    return StoryService(db)


def get_story_analyzer_service(
    db: AsyncSession = Depends(get_db),
) -> StoryAnalyzerService:
    """Dependency that builds a StoryAnalyzerService for the request session."""
    return StoryAnalyzerService(db)


def get_test_case_generator_service(
    db: AsyncSession = Depends(get_db),
) -> TestCaseGeneratorService:
    """Dependency that builds a TestCaseGeneratorService for the request session."""
    return TestCaseGeneratorService(db)


def get_qa_approval_service(
    db: AsyncSession = Depends(get_db),
) -> QAApprovalService:
    """Dependency that builds a QAApprovalService for the request session."""
    return QAApprovalService(db)


def get_bdd_generator_service(
    db: AsyncSession = Depends(get_db),
) -> BddGeneratorService:
    """Dependency that builds a BddGeneratorService for the request session."""
    return BddGeneratorService(db)


def get_playwright_generator_service(
    db: AsyncSession = Depends(get_db),
) -> PlaywrightGeneratorService:
    """Dependency that builds a PlaywrightGeneratorService for the request session."""
    return PlaywrightGeneratorService(db)


@router.get(
    "",
    response_model=StoryListResponse,
    status_code=status.HTTP_200_OK,
    summary="List stories",
    description=(
        "Return a paginated list of stories. "
        "Filter by status, story type, priority, sprint, and project. "
        "Search matches story key (`external_id`) and title."
    ),
    responses={
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def list_stories(
    pagination: PaginationParams = Depends(get_pagination),
    status_filter: Optional[StoryStatus] = Query(
        None,
        alias="status",
        description="Filter by story status",
    ),
    story_type: Optional[StoryType] = Query(
        None,
        description="Filter by story type",
    ),
    priority: Optional[Priority] = Query(
        None,
        description="Filter by priority",
    ),
    sprint_id: Optional[UUID] = Query(
        None,
        description="Filter by sprint ID",
    ),
    project_id: Optional[UUID] = Query(
        None,
        description="Filter by project ID",
    ),
    search: Optional[str] = Query(
        None,
        max_length=200,
        description="Search by story key (external_id) or title",
    ),
    service: StoryService = Depends(get_story_service),
) -> StoryListResponse:
    """List stories with pagination, filters, and search."""
    result = await service.list_stories(
        page=pagination.page,
        page_size=pagination.page_size,
        status=status_filter,
        story_type=story_type,
        priority=priority,
        sprint_id=sprint_id,
        project_id=project_id,
        search=search,
    )
    return StoryListResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )


@router.get(
    "/{story_id}",
    response_model=StoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get story by ID",
    description="Retrieve a single story by its UUID.",
    responses={
        404: {"model": ErrorResponse, "description": "Story not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def get_story(
    story_id: UUID,
    service: StoryService = Depends(get_story_service),
) -> StoryResponse:
    """Get a story by id."""
    return await service.get_story(story_id)


@router.post(
    "",
    response_model=StoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create story",
    description="Create a new story under an existing project.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid project or sprint"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_story(
    payload: StoryCreate,
    service: StoryService = Depends(get_story_service),
    _user: Optional[User] = Depends(require_write_access),
) -> StoryResponse:
    """Create a story."""
    return await service.create_story(payload)


@router.put(
    "/{story_id}",
    response_model=StoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update story",
    description="Update an existing story. Only provided fields are changed.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid project or sprint"},
        404: {"model": ErrorResponse, "description": "Story not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_story(
    story_id: UUID,
    payload: StoryUpdate,
    service: StoryService = Depends(get_story_service),
    _user: Optional[User] = Depends(require_write_access),
) -> StoryResponse:
    """Update a story."""
    return await service.update_story(story_id, payload)


@router.delete(
    "/{story_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete story",
    description="Soft-delete a story by ID.",
    responses={
        404: {"model": ErrorResponse, "description": "Story not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def delete_story(
    story_id: UUID,
    service: StoryService = Depends(get_story_service),
    _user: Optional[User] = Depends(require_write_access),
) -> MessageResponse:
    """Soft-delete a story."""
    await service.delete_story(story_id)
    return MessageResponse(message="Story deleted successfully", success=True)


@router.post(
    "/{story_id}/analyze",
    response_model=StoryAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Analyze story with AI",
    description=(
        "Run the AI Story Analyzer against a story. "
        "Persists complexity, risk, automation candidacy, dependencies, "
        "suggested tests, and a summary. Uses the AI Framework "
        "(logical model defaults to `default`)."
    ),
    tags=["Stories", "AI"],
    responses={
        400: {"model": ErrorResponse, "description": "AI or parse failure"},
        404: {"model": ErrorResponse, "description": "Story not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def analyze_story(
    story_id: UUID,
    payload: StoryAnalyzeRequest = Body(default=StoryAnalyzeRequest()),
    service: StoryAnalyzerService = Depends(get_story_analyzer_service),
) -> StoryAnalysisResponse:
    """Analyze a story and persist the result."""
    return await service.analyze_story(
        story_id,
        logical_model=payload.logical_model,
    )


@router.get(
    "/{story_id}/analysis",
    response_model=StoryAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Get latest story analysis",
    description="Return the most recently created AI analysis for a story.",
    tags=["Stories", "AI"],
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Story or analysis not found",
        },
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def get_story_analysis(
    story_id: UUID,
    service: StoryAnalyzerService = Depends(get_story_analyzer_service),
) -> StoryAnalysisResponse:
    """Get the latest analysis for a story."""
    return await service.get_latest_analysis(story_id)


@router.post(
    "/{story_id}/test-cases/generate",
    response_model=TestCaseGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate test cases with AI",
    description=(
        "Run the AI Test Case Generator against a story. "
        "Persists test cases across categories "
        "(positive, negative, boundary, api, security, database, "
        "accessibility, performance). Optionally uses the latest "
        "StoryAnalysis when present. Uses the AI Framework "
        "(logical model defaults to `default`)."
    ),
    tags=["Stories", "AI", "Test Cases"],
    responses={
        400: {"model": ErrorResponse, "description": "AI or parse failure"},
        404: {"model": ErrorResponse, "description": "Story not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def generate_test_cases(
    story_id: UUID,
    payload: TestCaseGenerateRequest = Body(default=TestCaseGenerateRequest()),
    service: TestCaseGeneratorService = Depends(get_test_case_generator_service),
) -> TestCaseGenerateResponse:
    """Generate and persist test cases for a story."""
    return await service.generate_test_cases(
        story_id,
        logical_model=payload.logical_model,
        categories=payload.categories,
    )


@router.get(
    "/{story_id}/test-cases",
    response_model=TestCaseListResponse,
    status_code=status.HTTP_200_OK,
    summary="List test cases for a story",
    description=(
        "Return a paginated list of test cases for a story. "
        "Optionally filter by category, source, and status "
        "(e.g. status=pending_review for QA review queue)."
    ),
    tags=["Stories", "Test Cases", "QA Approval"],
    responses={
        404: {"model": ErrorResponse, "description": "Story not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def list_story_test_cases(
    story_id: UUID,
    pagination: PaginationParams = Depends(get_pagination),
    category: Optional[TestCaseCategory] = Query(
        None,
        description="Filter by test case category",
    ),
    source: Optional[TestCaseSource] = Query(
        None,
        description="Filter by origin (ai, manual, imported)",
    ),
    status_filter: Optional[TestCaseStatus] = Query(
        None,
        alias="status",
        description="Filter by QA review status (draft, pending_review, approved, rejected)",
    ),
    service: TestCaseGeneratorService = Depends(get_test_case_generator_service),
) -> TestCaseListResponse:
    """List test cases for a story."""
    result = await service.list_test_cases(
        story_id,
        page=pagination.page,
        page_size=pagination.page_size,
        category=category,
        source=source,
        status=status_filter,
    )
    return TestCaseListResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )


@router.post(
    "/{story_id}/test-cases/approve-all",
    response_model=TestCaseApproveAllResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve all test cases for a story",
    description=(
        "Approve every draft, pending_review, or rejected test case for the story. "
        "When all cases are approved and a workflow run is at test_cases_generated, "
        "the workflow is advanced to qa_approved."
    ),
    tags=["Stories", "Test Cases", "QA Approval"],
    responses={
        400: {"model": ErrorResponse, "description": "No test cases"},
        404: {"model": ErrorResponse, "description": "Story not found"},
    },
)
async def approve_all_story_test_cases(
    story_id: UUID,
    service: QAApprovalService = Depends(get_qa_approval_service),
) -> TestCaseApproveAllResponse:
    """Approve all pending test cases for a story."""
    return await service.approve_all_for_story(story_id)


@router.post(
    "/{story_id}/bdd/generate",
    response_model=BddGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate BDD / Gherkin from test cases",
    description=(
        "Run the AI BDD Generator against a story's test cases. "
        "By default only approved cases are used; set include_drafts=true "
        "to also include draft and pending_review cases. "
        "Persists a BddFeature with full Gherkin content "
        "(Feature, Scenario, Scenario Outline, Examples, Tags)."
    ),
    tags=["Stories", "AI", "BDD"],
    responses={
        400: {
            "model": ErrorResponse,
            "description": "No eligible cases, AI, or parse failure",
        },
        404: {"model": ErrorResponse, "description": "Story not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def generate_bdd(
    story_id: UUID,
    payload: BddGenerateRequest = Body(default=BddGenerateRequest()),
    service: BddGeneratorService = Depends(get_bdd_generator_service),
) -> BddGenerateResponse:
    """Generate and persist a Gherkin feature for a story."""
    return await service.generate_bdd(
        story_id,
        logical_model=payload.logical_model,
        include_drafts=payload.include_drafts,
    )


@router.get(
    "/{story_id}/bdd",
    response_model=BddFeatureListResponse,
    status_code=status.HTTP_200_OK,
    summary="List BDD features for a story",
    description="Return a paginated list of generated Gherkin features for a story.",
    tags=["Stories", "BDD"],
    responses={
        404: {"model": ErrorResponse, "description": "Story not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def list_story_bdd_features(
    story_id: UUID,
    pagination: PaginationParams = Depends(get_pagination),
    service: BddGeneratorService = Depends(get_bdd_generator_service),
) -> BddFeatureListResponse:
    """List BDD features for a story."""
    result = await service.list_bdd_features(
        story_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return BddFeatureListResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )


@router.post(
    "/{story_id}/playwright/generate",
    response_model=PlaywrightGenerateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Playwright TypeScript automation",
    description=(
        "Run the AI Playwright Generator against a story's BDD features and/or "
        "test cases. Persists an AutomationArtifact with page objects, locators, "
        "fixtures, utilities, assertions, hooks, and specs as structured JSON "
        "plus file content strings. Browser execution is not performed."
    ),
    tags=["Stories", "AI", "Playwright"],
    responses={
        400: {
            "model": ErrorResponse,
            "description": "No eligible sources, AI, or parse failure",
        },
        404: {"model": ErrorResponse, "description": "Story not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def generate_playwright(
    story_id: UUID,
    payload: PlaywrightGenerateRequest = Body(default=PlaywrightGenerateRequest()),
    service: PlaywrightGeneratorService = Depends(get_playwright_generator_service),
) -> PlaywrightGenerateResponse:
    """Generate and persist Playwright TypeScript automation for a story."""
    return await service.generate_playwright(
        story_id,
        logical_model=payload.logical_model,
        use_bdd=payload.use_bdd,
        use_test_cases=payload.use_test_cases,
        include_drafts=payload.include_drafts,
    )


@router.get(
    "/{story_id}/playwright",
    response_model=AutomationArtifactListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Playwright artifacts for a story",
    description=(
        "Return a paginated list of generated Playwright automation artifacts "
        "for a story."
    ),
    tags=["Stories", "Playwright"],
    responses={
        404: {"model": ErrorResponse, "description": "Story not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def list_story_playwright_artifacts(
    story_id: UUID,
    pagination: PaginationParams = Depends(get_pagination),
    service: PlaywrightGeneratorService = Depends(get_playwright_generator_service),
) -> AutomationArtifactListResponse:
    """List Playwright automation artifacts for a story."""
    result = await service.list_artifacts(
        story_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return AutomationArtifactListResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )

"""
Execution Engine API Endpoints

Run stub tests, list/get execution history, retry failed executions,
analyze failures, and create Jira bugs.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import ErrorResponse
from app.models.enums import ExecutionStatus
from app.schemas.bug import CreateJiraBugRequest, CreateJiraBugResponse
from app.schemas.execution import (
    ExecutionDetailResponse,
    ExecutionListResponse,
    ExecutionRunRequest,
    ExecutionRunResponse,
)
from app.schemas.failure_analysis import (
    FailureAnalysisResponse,
    FailureAnalyzeRequest,
)
from app.services.bug_creation import BugCreationService
from app.services.execution_engine import ExecutionEngineService
from app.services.failure_analyzer import FailureAnalyzerService

router = APIRouter()


def get_execution_engine_service(
    db: AsyncSession = Depends(get_db),
) -> ExecutionEngineService:
    """Dependency that builds an ExecutionEngineService for the request session."""
    return ExecutionEngineService(db)


def get_failure_analyzer_service(
    db: AsyncSession = Depends(get_db),
) -> FailureAnalyzerService:
    """Dependency that builds a FailureAnalyzerService for the request session."""
    return FailureAnalyzerService(db)


def get_bug_creation_service(
    db: AsyncSession = Depends(get_db),
) -> BugCreationService:
    """Dependency that builds a BugCreationService for the request session."""
    return BugCreationService(db)


@router.post(
    "/run",
    response_model=ExecutionRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run tests (stub runner)",
    description=(
        "Execute test cases via the MVP stub/local runner (no real browsers). "
        "Provide exactly one of story_id, automation_artifact_id, or "
        "automation_job_id. When workflow_run_id is set and the run is in "
        "pull_request_created, emits ExecutionStarted then ExecutionCompleted."
    ),
    tags=["Executions"],
    responses={
        400: {"model": ErrorResponse, "description": "Invalid target or workflow state"},
        404: {"model": ErrorResponse, "description": "Target not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def run_executions(
    payload: ExecutionRunRequest,
    service: ExecutionEngineService = Depends(get_execution_engine_service),
) -> ExecutionRunResponse:
    """Trigger a simulated automation run and persist job + execution results."""
    return await service.run(payload)


@router.get(
    "",
    response_model=ExecutionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List execution history",
    description=(
        "Paginated execution history. Filter by automation_job_id, project_id, "
        "story_id, and/or status."
    ),
    tags=["Executions"],
    responses={
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def list_executions(
    automation_job_id: Optional[UUID] = Query(None),
    project_id: Optional[UUID] = Query(None),
    story_id: Optional[UUID] = Query(None),
    status_filter: Optional[ExecutionStatus] = Query(
        None,
        alias="status",
        description="Filter by execution status",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: ExecutionEngineService = Depends(get_execution_engine_service),
) -> ExecutionListResponse:
    """List persisted execution results (newest first)."""
    return await service.list_executions(
        automation_job_id=automation_job_id,
        project_id=project_id,
        story_id=story_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{execution_id}",
    response_model=ExecutionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Get execution by ID",
    description="Retrieve a single execution result with optional job summary.",
    tags=["Executions"],
    responses={
        404: {"model": ErrorResponse, "description": "Execution not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def get_execution(
    execution_id: UUID,
    service: ExecutionEngineService = Depends(get_execution_engine_service),
) -> ExecutionDetailResponse:
    """Get one execution by id."""
    return await service.get_execution(execution_id)


@router.post(
    "/{execution_id}/retry",
    response_model=ExecutionDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retry a failed execution",
    description=(
        "Re-run a failed, error, or blocked execution in place using the stub "
        "runner. Increments retry_count and updates the parent job aggregate."
    ),
    tags=["Executions"],
    responses={
        400: {"model": ErrorResponse, "description": "Execution is not retryable"},
        404: {"model": ErrorResponse, "description": "Execution not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def retry_execution(
    execution_id: UUID,
    service: ExecutionEngineService = Depends(get_execution_engine_service),
) -> ExecutionDetailResponse:
    """Retry a failed execution."""
    return await service.retry_execution(execution_id)


@router.post(
    "/{execution_id}/analyze-failure",
    response_model=FailureAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Analyze a failed execution with AI",
    description=(
        "Run AI Failure Analysis on a failed/error/blocked execution. "
        "Optional evidence fields (logs, screenshot/video/network/trace URLs) "
        "may be stub paths. Persists a FailureAnalysis including suggested_fix."
    ),
    tags=["Executions", "AI"],
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Not analyzable or AI failure",
        },
        404: {"model": ErrorResponse, "description": "Execution not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def analyze_failure(
    execution_id: UUID,
    payload: Optional[FailureAnalyzeRequest] = None,
    service: FailureAnalyzerService = Depends(get_failure_analyzer_service),
) -> FailureAnalysisResponse:
    """Analyze a failed execution and persist the FailureAnalysis result."""
    return await service.analyze_execution(
        execution_id,
        payload or FailureAnalyzeRequest(),
    )


@router.get(
    "/{execution_id}/failure-analysis",
    response_model=FailureAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Get latest failure analysis",
    description="Return the most recent FailureAnalysis for an execution.",
    tags=["Executions", "AI"],
    responses={
        404: {
            "model": ErrorResponse,
            "description": "Execution or analysis not found",
        },
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def get_failure_analysis(
    execution_id: UUID,
    service: FailureAnalyzerService = Depends(get_failure_analyzer_service),
) -> FailureAnalysisResponse:
    """Get the latest persisted failure analysis for an execution."""
    return await service.get_latest_analysis(execution_id)


@router.post(
    "/{execution_id}/create-jira-bug",
    response_model=CreateJiraBugResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Jira bug from a failed execution",
    description=(
        "Create a Bug issue in Jira from the execution and its failure analysis "
        "(latest analysis used when failure_analysis_id is omitted). "
        "Persists a local Bug with external_id and metadata "
        "(summary, logs link, execution link)."
    ),
    tags=["Executions", "Jira Connector"],
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Not filable, Jira not connected, or API error",
        },
        404: {
            "model": ErrorResponse,
            "description": "Execution or analysis not found",
        },
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_jira_bug(
    execution_id: UUID,
    payload: CreateJiraBugRequest,
    service: BugCreationService = Depends(get_bug_creation_service),
) -> CreateJiraBugResponse:
    """Create a Jira Bug and persist the local Bug entity."""
    return await service.create_jira_bug(execution_id, payload)

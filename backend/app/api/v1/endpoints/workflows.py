"""
Workflow API Endpoints

Start, advance, approve, retry, cancel, and inspect workflow runs.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import ErrorResponse
from app.orchestration.runtime import get_workflow_engine
from app.schemas.workflow import (
    WorkflowApproveRequest,
    WorkflowCancelRequest,
    WorkflowRetryRequest,
    WorkflowStartRequest,
    WorkflowStatusResponse,
)

router = APIRouter()


@router.post(
    "/start",
    response_model=WorkflowStatusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start workflow",
    description="Create a workflow run for a story and optionally mark it SYNCED.",
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)
async def start_workflow(
    payload: WorkflowStartRequest,
    db: AsyncSession = Depends(get_db),
) -> WorkflowStatusResponse:
    engine = get_workflow_engine(db)
    run = await engine.start(
        story_id=payload.story_id,
        mark_synced=payload.mark_synced,
        max_retries=payload.max_retries,
    )
    status_view = await engine.get_status(run.id)
    return WorkflowStatusResponse.model_validate(status_view)


@router.post(
    "/{run_id}/advance",
    response_model=WorkflowStatusResponse,
    summary="Advance workflow",
    description="Drive the next automatic stage (blocked at QA approval gate).",
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def advance_workflow(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> WorkflowStatusResponse:
    engine = get_workflow_engine(db)
    await engine.advance(run_id)
    return WorkflowStatusResponse.model_validate(await engine.get_status(run_id))


@router.post(
    "/{run_id}/approve",
    response_model=WorkflowStatusResponse,
    summary="QA approve / reject",
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def approve_workflow(
    run_id: UUID,
    payload: WorkflowApproveRequest,
    db: AsyncSession = Depends(get_db),
) -> WorkflowStatusResponse:
    engine = get_workflow_engine(db)
    await engine.approve(run_id, approved=payload.approved, reason=payload.reason)
    return WorkflowStatusResponse.model_validate(await engine.get_status(run_id))


@router.post(
    "/{run_id}/retry",
    response_model=WorkflowStatusResponse,
    summary="Retry workflow from state",
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def retry_workflow(
    run_id: UUID,
    payload: WorkflowRetryRequest,
    db: AsyncSession = Depends(get_db),
) -> WorkflowStatusResponse:
    engine = get_workflow_engine(db)
    await engine.retry(run_id, from_state=payload.from_state)
    return WorkflowStatusResponse.model_validate(await engine.get_status(run_id))


@router.post(
    "/{run_id}/cancel",
    response_model=WorkflowStatusResponse,
    summary="Cancel workflow",
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def cancel_workflow(
    run_id: UUID,
    payload: WorkflowCancelRequest,
    db: AsyncSession = Depends(get_db),
) -> WorkflowStatusResponse:
    engine = get_workflow_engine(db)
    await engine.cancel(run_id, reason=payload.reason)
    return WorkflowStatusResponse.model_validate(await engine.get_status(run_id))


@router.get(
    "/by-story/{story_id}",
    response_model=WorkflowStatusResponse,
    summary="Get latest workflow by story",
    responses={404: {"model": ErrorResponse}},
)
async def get_workflow_by_story(
    story_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> WorkflowStatusResponse:
    engine = get_workflow_engine(db)
    return WorkflowStatusResponse.model_validate(
        await engine.get_status_by_story(story_id)
    )


@router.get(
    "/{run_id}",
    response_model=WorkflowStatusResponse,
    summary="Get workflow status",
    responses={404: {"model": ErrorResponse}},
)
async def get_workflow(
    run_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> WorkflowStatusResponse:
    engine = get_workflow_engine(db)
    return WorkflowStatusResponse.model_validate(await engine.get_status(run_id))

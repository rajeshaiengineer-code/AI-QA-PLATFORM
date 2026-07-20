"""
Test Case API Endpoints

QA review: get/update, approve/reject, version history.
Story-scoped approve-all lives on the stories router.
"""

from uuid import UUID

from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import PaginationParams, get_db, get_pagination
from app.core.exceptions import ErrorResponse
from app.schemas.test_case import (
    TestCaseApproveRequest,
    TestCaseDecisionResponse,
    TestCaseRejectRequest,
    TestCaseResponse,
    TestCaseUpdate,
    TestCaseVersionListResponse,
)
from app.services.qa_approval import QAApprovalService

router = APIRouter()


def get_qa_approval_service(
    db: AsyncSession = Depends(get_db),
) -> QAApprovalService:
    """Dependency that builds a QAApprovalService for the request session."""
    return QAApprovalService(db)


@router.get(
    "/{test_case_id}",
    response_model=TestCaseResponse,
    status_code=status.HTTP_200_OK,
    summary="Get test case",
    description="Return a single test case by id.",
    responses={404: {"model": ErrorResponse, "description": "Not found"}},
    tags=["Test Cases", "QA Approval"],
)
async def get_test_case(
    test_case_id: UUID,
    service: QAApprovalService = Depends(get_qa_approval_service),
) -> TestCaseResponse:
    """Get a test case by id."""
    return await service.get_test_case(test_case_id)


@router.put(
    "/{test_case_id}",
    response_model=TestCaseResponse,
    status_code=status.HTTP_200_OK,
    summary="Update test case",
    description=(
        "Edit test case fields (title, steps, expected result, etc.). "
        "A version snapshot is stored before the change. "
        "Approved or rejected cases return to pending_review after an edit."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Bad request"},
        404: {"model": ErrorResponse, "description": "Not found"},
    },
    tags=["Test Cases", "QA Approval"],
)
async def update_test_case(
    test_case_id: UUID,
    payload: TestCaseUpdate = Body(...),
    service: QAApprovalService = Depends(get_qa_approval_service),
) -> TestCaseResponse:
    """Update a test case under QA review."""
    return await service.update_test_case(test_case_id, payload)


@router.post(
    "/{test_case_id}/approve",
    response_model=TestCaseDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve test case",
    description=(
        "Mark a test case as approved. When every test case for the story "
        "is approved and a workflow run is at test_cases_generated, the "
        "workflow is advanced to qa_approved."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Already approved"},
        404: {"model": ErrorResponse, "description": "Not found"},
    },
    tags=["Test Cases", "QA Approval"],
)
async def approve_test_case(
    test_case_id: UUID,
    payload: TestCaseApproveRequest = Body(default_factory=TestCaseApproveRequest),
    service: QAApprovalService = Depends(get_qa_approval_service),
) -> TestCaseDecisionResponse:
    """Approve an individual test case."""
    return await service.approve_test_case(test_case_id, note=payload.note)


@router.post(
    "/{test_case_id}/reject",
    response_model=TestCaseDecisionResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject test case",
    description="Mark a test case as rejected with an optional reason.",
    responses={
        400: {"model": ErrorResponse, "description": "Already rejected"},
        404: {"model": ErrorResponse, "description": "Not found"},
    },
    tags=["Test Cases", "QA Approval"],
)
async def reject_test_case(
    test_case_id: UUID,
    payload: TestCaseRejectRequest = Body(default_factory=TestCaseRejectRequest),
    service: QAApprovalService = Depends(get_qa_approval_service),
) -> TestCaseDecisionResponse:
    """Reject an individual test case."""
    return await service.reject_test_case(test_case_id, reason=payload.reason)


@router.get(
    "/{test_case_id}/versions",
    response_model=TestCaseVersionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List test case versions",
    description="Return paginated version history for a test case (newest first).",
    responses={404: {"model": ErrorResponse, "description": "Not found"}},
    tags=["Test Cases", "QA Approval"],
)
async def list_test_case_versions(
    test_case_id: UUID,
    pagination: PaginationParams = Depends(get_pagination),
    service: QAApprovalService = Depends(get_qa_approval_service),
) -> TestCaseVersionListResponse:
    """List version history for a test case."""
    result = await service.list_versions(
        test_case_id,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return TestCaseVersionListResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )

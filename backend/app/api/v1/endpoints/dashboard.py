"""
Dashboard API Endpoints

Org/project-scoped reporting aggregates for the QA dashboard.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import ErrorResponse
from app.schemas.dashboard import (
    AiMetricsResponse,
    CoverageResponse,
    DashboardSummaryResponse,
    ExecutionTrendsResponse,
)
from app.services.dashboard import DashboardService

router = APIRouter()


def get_dashboard_service(db: AsyncSession = Depends(get_db)) -> DashboardService:
    return DashboardService(db)


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Dashboard summary counts",
    description=(
        "Return org/project-scoped entity counts: projects, sprints, stories, "
        "test cases, executions, automation jobs, plus status breakdowns."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid scope combination"},
        404: {"model": ErrorResponse, "description": "Organization or project not found"},
    },
)
async def get_dashboard_summary(
    organization_id: Optional[UUID] = Query(
        None,
        description="Scope to an organization",
    ),
    project_id: Optional[UUID] = Query(
        None,
        description="Scope to a project (must belong to organization_id when both set)",
    ),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardSummaryResponse:
    return await service.get_summary(
        organization_id=organization_id,
        project_id=project_id,
    )


@router.get(
    "/execution-trends",
    response_model=ExecutionTrendsResponse,
    status_code=status.HTTP_200_OK,
    summary="Execution trend time series",
    description=(
        "Return execution outcome counts in day or week buckets over the last N days."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid days/bucket/scope"},
        404: {"model": ErrorResponse, "description": "Organization or project not found"},
    },
)
async def get_execution_trends(
    organization_id: Optional[UUID] = Query(
        None,
        description="Scope to an organization",
    ),
    project_id: Optional[UUID] = Query(
        None,
        description="Scope to a project",
    ),
    days: int = Query(
        30,
        ge=1,
        le=365,
        description="Lookback window in days (1–365)",
    ),
    bucket: str = Query(
        "day",
        description="Time bucket size: day or week",
    ),
    service: DashboardService = Depends(get_dashboard_service),
) -> ExecutionTrendsResponse:
    return await service.get_execution_trends(
        organization_id=organization_id,
        project_id=project_id,
        days=days,
        bucket=bucket,
    )


@router.get(
    "/coverage",
    response_model=CoverageResponse,
    status_code=status.HTTP_200_OK,
    summary="Story and test-case coverage",
    description=(
        "Stories with/without test cases, test-case status breakdown, "
        "and approved / coverage ratios."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid scope combination"},
        404: {"model": ErrorResponse, "description": "Organization or project not found"},
    },
)
async def get_coverage(
    organization_id: Optional[UUID] = Query(
        None,
        description="Scope to an organization",
    ),
    project_id: Optional[UUID] = Query(
        None,
        description="Scope to a project",
    ),
    service: DashboardService = Depends(get_dashboard_service),
) -> CoverageResponse:
    return await service.get_coverage(
        organization_id=organization_id,
        project_id=project_id,
    )


@router.get(
    "/ai-metrics",
    response_model=AiMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="AI pipeline metrics",
    description=(
        "Counts of story analyses, AI-generated test cases, "
        "BDD feature artifacts, and Playwright automation artifacts."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid scope combination"},
        404: {"model": ErrorResponse, "description": "Organization or project not found"},
    },
)
async def get_ai_metrics(
    organization_id: Optional[UUID] = Query(
        None,
        description="Scope to an organization",
    ),
    project_id: Optional[UUID] = Query(
        None,
        description="Scope to a project",
    ),
    service: DashboardService = Depends(get_dashboard_service),
) -> AiMetricsResponse:
    return await service.get_ai_metrics(
        organization_id=organization_id,
        project_id=project_id,
    )

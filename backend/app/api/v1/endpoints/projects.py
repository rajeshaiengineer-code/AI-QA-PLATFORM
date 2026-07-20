"""
Project API Endpoints

CRUD operations and dashboard stats for Project management.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import PaginationParams, get_db, get_pagination
from app.core.exceptions import ErrorResponse
from app.core.rbac import require_write_access
from app.models.user import User
from app.schemas.base import MessageResponse
from app.schemas.project import (
    ProjectCreate,
    ProjectDashboardStats,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.project import ProjectService

router = APIRouter()


def get_project_service(db: AsyncSession = Depends(get_db)) -> ProjectService:
    return ProjectService(db)


@router.get(
    "",
    response_model=ProjectListResponse,
    status_code=status.HTTP_200_OK,
    summary="List projects",
    description=(
        "Return a paginated list of projects. "
        "Filter by organization and active flag. Search matches name and key."
    ),
    responses={422: {"model": ErrorResponse, "description": "Validation error"}},
)
async def list_projects(
    pagination: PaginationParams = Depends(get_pagination),
    organization_id: Optional[UUID] = Query(
        None,
        description="Filter by organization ID",
    ),
    is_active: Optional[bool] = Query(
        None,
        description="Filter by active flag",
    ),
    search: Optional[str] = Query(
        None,
        max_length=200,
        description="Search by project name or key",
    ),
    service: ProjectService = Depends(get_project_service),
) -> ProjectListResponse:
    result = await service.list_projects(
        page=pagination.page,
        page_size=pagination.page_size,
        organization_id=organization_id,
        is_active=is_active,
        search=search,
    )
    return ProjectListResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create project",
    description="Create a project under an existing organization. Key must be unique per org.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid organization or duplicate key"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_project(
    payload: ProjectCreate,
    service: ProjectService = Depends(get_project_service),
    _user: Optional[User] = Depends(require_write_access),
) -> ProjectResponse:
    return await service.create_project(payload)


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Get project",
    responses={404: {"model": ErrorResponse, "description": "Project not found"}},
)
async def get_project(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    return await service.get_project(project_id)


@router.get(
    "/{project_id}/dashboard",
    response_model=ProjectDashboardStats,
    status_code=status.HTTP_200_OK,
    summary="Project dashboard stats",
    description="Story and sprint counts for a project dashboard.",
    responses={404: {"model": ErrorResponse, "description": "Project not found"}},
)
async def get_project_dashboard(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service),
) -> ProjectDashboardStats:
    return await service.get_dashboard_stats(project_id)


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Update project",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid organization or duplicate key"},
        404: {"model": ErrorResponse, "description": "Project not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    service: ProjectService = Depends(get_project_service),
    _user: Optional[User] = Depends(require_write_access),
) -> ProjectResponse:
    return await service.update_project(project_id, payload)


@router.delete(
    "/{project_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete project",
    description="Soft-delete a project.",
    responses={404: {"model": ErrorResponse, "description": "Project not found"}},
)
async def delete_project(
    project_id: UUID,
    service: ProjectService = Depends(get_project_service),
    _user: Optional[User] = Depends(require_write_access),
) -> MessageResponse:
    await service.delete_project(project_id)
    return MessageResponse(message="Project deleted successfully")

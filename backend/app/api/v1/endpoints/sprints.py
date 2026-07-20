"""
Sprint API Endpoints

CRUD operations for Sprint management.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import PaginationParams, get_db, get_pagination
from app.core.exceptions import ErrorResponse
from app.schemas.base import MessageResponse
from app.schemas.sprint import (
    SprintCreate,
    SprintListResponse,
    SprintResponse,
    SprintUpdate,
)
from app.services.sprint import SprintService

router = APIRouter()


def get_sprint_service(db: AsyncSession = Depends(get_db)) -> SprintService:
    return SprintService(db)


@router.get(
    "",
    response_model=SprintListResponse,
    status_code=status.HTTP_200_OK,
    summary="List sprints",
    description=(
        "Return a paginated list of sprints. "
        "Filter by project and active flag. Search matches name and goal."
    ),
    responses={422: {"model": ErrorResponse, "description": "Validation error"}},
)
async def list_sprints(
    pagination: PaginationParams = Depends(get_pagination),
    project_id: Optional[UUID] = Query(
        None,
        description="Filter by project ID",
    ),
    is_active: Optional[bool] = Query(
        None,
        description="Filter by active flag",
    ),
    search: Optional[str] = Query(
        None,
        max_length=200,
        description="Search by sprint name or goal",
    ),
    service: SprintService = Depends(get_sprint_service),
) -> SprintListResponse:
    result = await service.list_sprints(
        page=pagination.page,
        page_size=pagination.page_size,
        project_id=project_id,
        is_active=is_active,
        search=search,
    )
    return SprintListResponse(
        items=result.items,
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        total_pages=result.total_pages,
    )


@router.post(
    "",
    response_model=SprintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create sprint",
    description="Create a sprint under an existing project.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid project reference"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def create_sprint(
    payload: SprintCreate,
    service: SprintService = Depends(get_sprint_service),
) -> SprintResponse:
    return await service.create_sprint(payload)


@router.get(
    "/{sprint_id}",
    response_model=SprintResponse,
    status_code=status.HTTP_200_OK,
    summary="Get sprint",
    responses={404: {"model": ErrorResponse, "description": "Sprint not found"}},
)
async def get_sprint(
    sprint_id: UUID,
    service: SprintService = Depends(get_sprint_service),
) -> SprintResponse:
    return await service.get_sprint(sprint_id)


@router.put(
    "/{sprint_id}",
    response_model=SprintResponse,
    status_code=status.HTTP_200_OK,
    summary="Update sprint",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid project or dates"},
        404: {"model": ErrorResponse, "description": "Sprint not found"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def update_sprint(
    sprint_id: UUID,
    payload: SprintUpdate,
    service: SprintService = Depends(get_sprint_service),
) -> SprintResponse:
    return await service.update_sprint(sprint_id, payload)


@router.delete(
    "/{sprint_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete sprint",
    description="Soft-delete a sprint.",
    responses={404: {"model": ErrorResponse, "description": "Sprint not found"}},
)
async def delete_sprint(
    sprint_id: UUID,
    service: SprintService = Depends(get_sprint_service),
) -> MessageResponse:
    await service.delete_sprint(sprint_id)
    return MessageResponse(message="Sprint deleted successfully")

"""
Project Service

Business orchestration for Project CRUD and dashboard stats.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.project import Project
from app.repositories.project import ProjectRepository
from app.schemas.base import PaginatedResponse
from app.schemas.project import (
    ProjectCreate,
    ProjectDashboardStats,
    ProjectResponse,
    ProjectUpdate,
)


class ProjectService:
    """Service layer for Project management."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = ProjectRepository(session)

    async def list_projects(
        self,
        *,
        page: int,
        page_size: int,
        organization_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse[ProjectResponse]:
        offset = (page - 1) * page_size
        projects, total = await self.repository.list_filtered(
            offset=offset,
            limit=page_size,
            organization_id=organization_id,
            is_active=is_active,
            search=search,
        )
        items = [ProjectResponse.model_validate(p) for p in projects]
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_project(self, project_id: UUID) -> ProjectResponse:
        project = await self.repository.get_by_id(project_id)
        if project is None:
            raise NotFoundException("Project", str(project_id))
        return ProjectResponse.model_validate(project)

    async def get_dashboard_stats(self, project_id: UUID) -> ProjectDashboardStats:
        project = await self.repository.get_by_id(project_id)
        if project is None:
            raise NotFoundException("Project", str(project_id))

        return ProjectDashboardStats(
            project_id=project_id,
            story_total=await self.repository.count_stories(project_id),
            story_by_status=await self.repository.count_stories_by_status(project_id),
            sprint_total=await self.repository.count_sprints(project_id),
            active_sprint_total=await self.repository.count_sprints(
                project_id,
                active_only=True,
            ),
        )

    async def create_project(self, payload: ProjectCreate) -> ProjectResponse:
        if not await self.repository.organization_exists(payload.organization_id):
            raise BadRequestException(
                f"Organization '{payload.organization_id}' does not exist"
            )

        existing = await self.repository.get_by_org_and_key(
            payload.organization_id,
            payload.key,
        )
        if existing is not None:
            raise BadRequestException(
                f"Project key '{payload.key}' already exists in this organization"
            )

        project = Project(
            organization_id=payload.organization_id,
            name=payload.name,
            key=payload.key,
            description=payload.description,
            external_id=payload.external_id,
            is_active=payload.is_active,
        )
        created = await self.repository.add(project)
        return ProjectResponse.model_validate(created)

    async def update_project(
        self,
        project_id: UUID,
        payload: ProjectUpdate,
    ) -> ProjectResponse:
        project = await self.repository.get_by_id(project_id)
        if project is None:
            raise NotFoundException("Project", str(project_id))

        data = payload.model_dump(exclude_unset=True)

        org_id = data.get("organization_id", project.organization_id)
        if "organization_id" in data:
            if not await self.repository.organization_exists(org_id):
                raise BadRequestException(
                    f"Organization '{org_id}' does not exist"
                )

        new_key = data.get("key", project.key)
        if "key" in data or "organization_id" in data:
            conflict = await self.repository.get_by_org_and_key(
                org_id,
                new_key,
                exclude_id=project.id,
            )
            if conflict is not None:
                raise BadRequestException(
                    f"Project key '{new_key}' already exists in this organization"
                )

        for field, value in data.items():
            setattr(project, field, value)

        await self.session.flush()
        column_keys = [column.key for column in project.__table__.columns]
        await self.session.refresh(project, attribute_names=column_keys)
        return ProjectResponse.model_validate(project)

    async def delete_project(self, project_id: UUID) -> None:
        project = await self.repository.get_by_id(project_id)
        if project is None:
            raise NotFoundException("Project", str(project_id))
        await self.repository.delete(project, soft=True)

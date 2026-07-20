"""
Project Repository

Async data-access for Project entities.
"""

from typing import Dict, Optional, Sequence
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.models.organization import Organization
from app.models.project import Project
from app.models.sprint import Sprint
from app.models.story import Story
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    """Repository for Project CRUD and filtered listing."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Project)

    def _base_query(self) -> Select[tuple[Project]]:
        return (
            select(Project)
            .options(
                noload(Project.organization),
                noload(Project.sprints),
                noload(Project.stories),
                noload(Project.automation_jobs),
                noload(Project.bugs),
            )
            .where(Project.is_deleted.is_(False))
        )

    async def get_by_id(
        self,
        entity_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Optional[Project]:
        stmt = (
            select(Project)
            .options(
                noload(Project.organization),
                noload(Project.sprints),
                noload(Project.stories),
                noload(Project.automation_jobs),
                noload(Project.bugs),
            )
            .where(Project.id == entity_id)
        )
        if not include_deleted:
            stmt = stmt.where(Project.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_filtered(
        self,
        *,
        offset: int,
        limit: int,
        organization_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> tuple[Sequence[Project], int]:
        stmt = self._base_query()
        count_stmt = (
            select(func.count())
            .select_from(Project)
            .where(Project.is_deleted.is_(False))
        )

        if organization_id is not None:
            stmt = stmt.where(Project.organization_id == organization_id)
            count_stmt = count_stmt.where(Project.organization_id == organization_id)
        if is_active is not None:
            stmt = stmt.where(Project.is_active.is_(is_active))
            count_stmt = count_stmt.where(Project.is_active.is_(is_active))
        if search:
            pattern = f"%{search.strip()}%"
            search_filter = or_(
                Project.name.ilike(pattern),
                Project.key.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        stmt = stmt.order_by(Project.name.asc()).offset(offset).limit(limit)
        rows = await self.session.execute(stmt)
        total = await self.session.scalar(count_stmt)
        return rows.scalars().all(), int(total or 0)

    async def get_by_org_and_key(
        self,
        organization_id: UUID,
        key: str,
        *,
        exclude_id: Optional[UUID] = None,
    ) -> Optional[Project]:
        stmt = self._base_query().where(
            Project.organization_id == organization_id,
            Project.key == key,
        )
        if exclude_id is not None:
            stmt = stmt.where(Project.id != exclude_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def organization_exists(self, organization_id: UUID) -> bool:
        stmt = select(Organization.id).where(
            Organization.id == organization_id,
            Organization.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def count_stories(self, project_id: UUID) -> int:
        stmt = select(func.count()).select_from(Story).where(
            Story.project_id == project_id,
            Story.is_deleted.is_(False),
        )
        return int(await self.session.scalar(stmt) or 0)

    async def count_stories_by_status(self, project_id: UUID) -> Dict[str, int]:
        stmt = (
            select(Story.status, func.count())
            .where(
                Story.project_id == project_id,
                Story.is_deleted.is_(False),
            )
            .group_by(Story.status)
        )
        rows = await self.session.execute(stmt)
        result: Dict[str, int] = {}
        for status, count in rows.all():
            key = status.value if hasattr(status, "value") else str(status)
            result[key] = int(count)
        return result

    async def count_sprints(
        self,
        project_id: UUID,
        *,
        active_only: bool = False,
    ) -> int:
        stmt = select(func.count()).select_from(Sprint).where(
            Sprint.project_id == project_id,
            Sprint.is_deleted.is_(False),
        )
        if active_only:
            stmt = stmt.where(Sprint.is_active.is_(True))
        return int(await self.session.scalar(stmt) or 0)

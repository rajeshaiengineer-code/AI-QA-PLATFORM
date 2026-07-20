"""
Story Repository

Async data-access for Story entities.
"""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.models.enums import Priority, StoryStatus, StoryType
from app.models.project import Project
from app.models.sprint import Sprint
from app.models.story import Story
from app.repositories.base import BaseRepository


class StoryRepository(BaseRepository[Story]):
    """Repository for Story CRUD and filtered listing."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Story)

    def _base_query(self) -> Select[tuple[Story]]:
        """Story query that avoids eager-loading child collections."""
        return (
            select(Story)
            .options(
                noload(Story.acceptance_criteria),
                noload(Story.test_cases),
                noload(Story.bugs),
                noload(Story.analyses),
                noload(Story.project),
                noload(Story.sprint),
            )
            .where(Story.is_deleted.is_(False))
        )

    async def get_by_id(
        self,
        entity_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Optional[Story]:
        """Fetch a story by id without loading relationships."""
        stmt = (
            select(Story)
            .options(
                noload(Story.acceptance_criteria),
                noload(Story.test_cases),
                noload(Story.bugs),
                noload(Story.analyses),
                noload(Story.project),
                noload(Story.sprint),
            )
            .where(Story.id == entity_id)
        )
        if not include_deleted:
            stmt = stmt.where(Story.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_filtered(
        self,
        *,
        offset: int,
        limit: int,
        status: Optional[StoryStatus] = None,
        story_type: Optional[StoryType] = None,
        priority: Optional[Priority] = None,
        sprint_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        search: Optional[str] = None,
    ) -> tuple[Sequence[Story], int]:
        """
        List stories with filters, search, and pagination.

        Search matches title and external_id (story key) case-insensitively.
        """
        stmt = self._base_query()
        stmt = self._apply_filters(
            stmt,
            status=status,
            story_type=story_type,
            priority=priority,
            sprint_id=sprint_id,
            project_id=project_id,
            search=search,
        )

        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = stmt.order_by(Story.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    def _apply_filters(
        self,
        stmt: Select[tuple[Story]],
        *,
        status: Optional[StoryStatus],
        story_type: Optional[StoryType],
        priority: Optional[Priority],
        sprint_id: Optional[UUID],
        project_id: Optional[UUID],
        search: Optional[str],
    ) -> Select[tuple[Story]]:
        if status is not None:
            stmt = stmt.where(Story.status == status)
        if story_type is not None:
            stmt = stmt.where(Story.story_type == story_type)
        if priority is not None:
            stmt = stmt.where(Story.priority == priority)
        if sprint_id is not None:
            stmt = stmt.where(Story.sprint_id == sprint_id)
        if project_id is not None:
            stmt = stmt.where(Story.project_id == project_id)
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Story.title.ilike(pattern),
                    Story.external_id.ilike(pattern),
                )
            )
        return stmt

    async def project_exists(self, project_id: UUID) -> bool:
        """Return True if a non-deleted project exists."""
        stmt = select(Project.id).where(
            Project.id == project_id,
            Project.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_sprint(self, sprint_id: UUID) -> Optional[Sprint]:
        """Fetch a non-deleted sprint by id (no relationship loading)."""
        stmt = (
            select(Sprint)
            .options(
                noload(Sprint.stories),
                noload(Sprint.automation_jobs),
                noload(Sprint.project),
            )
            .where(
                Sprint.id == sprint_id,
                Sprint.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

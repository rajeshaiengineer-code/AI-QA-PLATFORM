"""
Sprint Repository

Async data-access for Sprint entities.
"""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.models.project import Project
from app.models.sprint import Sprint
from app.repositories.base import BaseRepository


class SprintRepository(BaseRepository[Sprint]):
    """Repository for Sprint CRUD and filtered listing."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Sprint)

    def _base_query(self) -> Select[tuple[Sprint]]:
        return (
            select(Sprint)
            .options(
                noload(Sprint.project),
                noload(Sprint.stories),
                noload(Sprint.automation_jobs),
            )
            .where(Sprint.is_deleted.is_(False))
        )

    async def get_by_id(
        self,
        entity_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Optional[Sprint]:
        stmt = (
            select(Sprint)
            .options(
                noload(Sprint.project),
                noload(Sprint.stories),
                noload(Sprint.automation_jobs),
            )
            .where(Sprint.id == entity_id)
        )
        if not include_deleted:
            stmt = stmt.where(Sprint.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_filtered(
        self,
        *,
        offset: int,
        limit: int,
        project_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> tuple[Sequence[Sprint], int]:
        stmt = self._base_query()
        count_stmt = (
            select(func.count())
            .select_from(Sprint)
            .where(Sprint.is_deleted.is_(False))
        )

        if project_id is not None:
            stmt = stmt.where(Sprint.project_id == project_id)
            count_stmt = count_stmt.where(Sprint.project_id == project_id)
        if is_active is not None:
            stmt = stmt.where(Sprint.is_active.is_(is_active))
            count_stmt = count_stmt.where(Sprint.is_active.is_(is_active))
        if search:
            pattern = f"%{search.strip()}%"
            search_filter = or_(
                Sprint.name.ilike(pattern),
                Sprint.goal.ilike(pattern),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        stmt = stmt.order_by(Sprint.name.asc()).offset(offset).limit(limit)
        rows = await self.session.execute(stmt)
        total = await self.session.scalar(count_stmt)
        return rows.scalars().all(), int(total or 0)

    async def project_exists(self, project_id: UUID) -> bool:
        stmt = select(Project.id).where(
            Project.id == project_id,
            Project.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

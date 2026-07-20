"""
Story Analysis Repository

Async data-access for StoryAnalysis entities.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.models.story_analysis import StoryAnalysis
from app.repositories.base import BaseRepository


class StoryAnalysisRepository(BaseRepository[StoryAnalysis]):
    """Repository for StoryAnalysis CRUD and latest-by-story lookups."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, StoryAnalysis)

    async def get_by_id(
        self,
        entity_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Optional[StoryAnalysis]:
        stmt = (
            select(StoryAnalysis)
            .options(noload(StoryAnalysis.story))
            .where(StoryAnalysis.id == entity_id)
        )
        if not include_deleted:
            stmt = stmt.where(StoryAnalysis.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_for_story(
        self,
        story_id: UUID,
    ) -> Optional[StoryAnalysis]:
        """Return the most recently created analysis for a story."""
        stmt = (
            select(StoryAnalysis)
            .options(noload(StoryAnalysis.story))
            .where(
                StoryAnalysis.story_id == story_id,
                StoryAnalysis.is_deleted.is_(False),
            )
            .order_by(
                StoryAnalysis.created_at.desc(),
                StoryAnalysis.id.desc(),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

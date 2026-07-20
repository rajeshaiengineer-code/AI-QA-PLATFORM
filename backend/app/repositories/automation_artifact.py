"""
Automation Artifact Repository

Async data-access for AutomationArtifact entities.
"""

from typing import Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.models.automation_artifact import AutomationArtifact
from app.repositories.base import BaseRepository


class AutomationArtifactRepository(BaseRepository[AutomationArtifact]):
    """Repository for AutomationArtifact CRUD and story-scoped listing."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AutomationArtifact)

    def _base_query(self) -> Select:
        return (
            select(AutomationArtifact)
            .options(noload(AutomationArtifact.story))
            .where(AutomationArtifact.is_deleted.is_(False))
        )

    async def get_by_id(
        self,
        entity_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Optional[AutomationArtifact]:
        stmt = (
            select(AutomationArtifact)
            .options(noload(AutomationArtifact.story))
            .where(AutomationArtifact.id == entity_id)
        )
        if not include_deleted:
            stmt = stmt.where(AutomationArtifact.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_story(
        self,
        story_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[Sequence[AutomationArtifact], int]:
        """List automation artifacts for a story (newest first) with pagination."""
        stmt = self._base_query().where(AutomationArtifact.story_id == story_id)

        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            stmt.order_by(
                AutomationArtifact.created_at.desc(),
                AutomationArtifact.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def get_latest_for_story(
        self,
        story_id: UUID,
    ) -> Optional[AutomationArtifact]:
        """Return the newest automation artifact for a story, if any."""
        items, _ = await self.list_for_story(story_id, offset=0, limit=1)
        return items[0] if items else None

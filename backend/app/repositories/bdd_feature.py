"""
BDD Feature Repository

Async data-access for BddFeature entities.
"""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.models.bdd_feature import BddFeature
from app.repositories.base import BaseRepository


class BddFeatureRepository(BaseRepository[BddFeature]):
    """Repository for BddFeature CRUD and story-scoped listing."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BddFeature)

    def _base_query(self) -> Select:
        return (
            select(BddFeature)
            .options(noload(BddFeature.story))
            .where(BddFeature.is_deleted.is_(False))
        )

    async def get_by_id(
        self,
        entity_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Optional[BddFeature]:
        stmt = (
            select(BddFeature)
            .options(noload(BddFeature.story))
            .where(BddFeature.id == entity_id)
        )
        if not include_deleted:
            stmt = stmt.where(BddFeature.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_story(
        self,
        story_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[BddFeature], int]:
        """List BDD features for a story (newest first) with pagination."""
        stmt = self._base_query().where(BddFeature.story_id == story_id)

        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            stmt.order_by(
                BddFeature.created_at.desc(),
                BddFeature.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

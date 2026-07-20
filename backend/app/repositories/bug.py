"""
Bug Repository

Async data-access for Bug entities.
"""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.models.bug import Bug
from app.repositories.base import BaseRepository


class BugRepository(BaseRepository[Bug]):
    """Repository for Bug CRUD and execution-scoped lookups."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Bug)

    async def get_by_id(
        self,
        entity_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Optional[Bug]:
        stmt = (
            select(Bug)
            .options(
                noload(Bug.project),
                noload(Bug.story),
                noload(Bug.test_case),
                noload(Bug.execution),
                noload(Bug.failure_analysis),
            )
            .where(Bug.id == entity_id)
        )
        if not include_deleted:
            stmt = stmt.where(Bug.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_execution(self, execution_id: UUID) -> Sequence[Bug]:
        stmt = (
            select(Bug)
            .options(
                noload(Bug.project),
                noload(Bug.story),
                noload(Bug.test_case),
                noload(Bug.execution),
                noload(Bug.failure_analysis),
            )
            .where(
                Bug.execution_id == execution_id,
                Bug.is_deleted.is_(False),
            )
            .order_by(Bug.created_at.desc(), Bug.id.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

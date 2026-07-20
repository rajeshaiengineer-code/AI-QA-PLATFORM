"""
Failure Analysis Repository

Async data-access for FailureAnalysis entities.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.models.failure_analysis import FailureAnalysis
from app.repositories.base import BaseRepository


class FailureAnalysisRepository(BaseRepository[FailureAnalysis]):
    """Repository for FailureAnalysis CRUD and latest-by-execution lookups."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, FailureAnalysis)

    async def get_by_id(
        self,
        entity_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Optional[FailureAnalysis]:
        stmt = (
            select(FailureAnalysis)
            .options(
                noload(FailureAnalysis.execution),
                noload(FailureAnalysis.bugs),
            )
            .where(FailureAnalysis.id == entity_id)
        )
        if not include_deleted:
            stmt = stmt.where(FailureAnalysis.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_for_execution(
        self,
        execution_id: UUID,
    ) -> Optional[FailureAnalysis]:
        """Return the most recently created analysis for an execution."""
        stmt = (
            select(FailureAnalysis)
            .options(
                noload(FailureAnalysis.execution),
                noload(FailureAnalysis.bugs),
            )
            .where(
                FailureAnalysis.execution_id == execution_id,
                FailureAnalysis.is_deleted.is_(False),
            )
            .order_by(
                FailureAnalysis.created_at.desc(),
                FailureAnalysis.id.desc(),
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

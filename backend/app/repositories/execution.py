"""
Execution Repository

Async data-access for Execution entities.
"""

from typing import Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from app.models.automation_job import AutomationJob
from app.models.enums import ExecutionStatus
from app.models.execution import Execution
from app.models.test_case import TestCase
from app.repositories.base import BaseRepository


class ExecutionRepository(BaseRepository[Execution]):
    """Repository for Execution CRUD, history listing, and retries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Execution)

    def _base_query(self) -> Select:
        return (
            select(Execution)
            .options(
                noload(Execution.automation_job),
                noload(Execution.test_case),
                noload(Execution.bugs),
                noload(Execution.failure_analyses),
            )
            .where(Execution.is_deleted.is_(False))
        )

    async def get_by_id(
        self,
        entity_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Optional[Execution]:
        stmt = (
            select(Execution)
            .options(
                selectinload(Execution.automation_job).options(
                    noload(AutomationJob.executions),
                    noload(AutomationJob.project),
                    noload(AutomationJob.sprint),
                ),
                noload(Execution.test_case),
                noload(Execution.bugs),
                noload(Execution.failure_analyses),
            )
            .where(Execution.id == entity_id)
        )
        if not include_deleted:
            stmt = stmt.where(Execution.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_executions(
        self,
        *,
        automation_job_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        story_id: Optional[UUID] = None,
        status: Optional[ExecutionStatus] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[Sequence[Execution], int]:
        stmt = self._base_query()

        if automation_job_id is not None:
            stmt = stmt.where(Execution.automation_job_id == automation_job_id)

        if status is not None:
            stmt = stmt.where(Execution.status == status)

        if project_id is not None:
            stmt = stmt.join(
                AutomationJob,
                AutomationJob.id == Execution.automation_job_id,
            ).where(
                AutomationJob.project_id == project_id,
                AutomationJob.is_deleted.is_(False),
            )

        if story_id is not None:
            stmt = stmt.join(
                TestCase,
                TestCase.id == Execution.test_case_id,
            ).where(
                TestCase.story_id == story_id,
                TestCase.is_deleted.is_(False),
            )

        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            stmt.order_by(
                Execution.created_at.desc(),
                Execution.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().unique().all(), total

    async def list_for_job(self, automation_job_id: UUID) -> Sequence[Execution]:
        stmt = (
            self._base_query()
            .where(Execution.automation_job_id == automation_job_id)
            .order_by(Execution.created_at.asc(), Execution.id.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

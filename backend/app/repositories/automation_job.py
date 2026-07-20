"""
AutomationJob Repository

Async data-access for AutomationJob entities.
"""

from typing import Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from app.models.automation_job import AutomationJob
from app.models.enums import AutomationStatus
from app.models.execution import Execution
from app.repositories.base import BaseRepository


class AutomationJobRepository(BaseRepository[AutomationJob]):
    """Repository for AutomationJob CRUD and filtered listing."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AutomationJob)

    def _execution_load(self):
        return selectinload(AutomationJob.executions).options(
            noload(Execution.bugs),
            noload(Execution.test_case),
            noload(Execution.automation_job),
        )

    def _base_query(self) -> Select:
        return (
            select(AutomationJob)
            .options(
                noload(AutomationJob.project),
                noload(AutomationJob.sprint),
                self._execution_load(),
            )
            .where(AutomationJob.is_deleted.is_(False))
        )

    async def get_by_id(
        self,
        entity_id: UUID,
        *,
        include_deleted: bool = False,
        with_executions: bool = True,
    ) -> Optional[AutomationJob]:
        options = [
            noload(AutomationJob.project),
            noload(AutomationJob.sprint),
        ]
        if with_executions:
            options.append(self._execution_load())
        else:
            options.append(noload(AutomationJob.executions))

        stmt = select(AutomationJob).options(*options).where(
            AutomationJob.id == entity_id
        )
        if not include_deleted:
            stmt = stmt.where(AutomationJob.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        *,
        project_id: Optional[UUID] = None,
        status: Optional[AutomationStatus] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[Sequence[AutomationJob], int]:
        stmt = self._base_query()
        if project_id is not None:
            stmt = stmt.where(AutomationJob.project_id == project_id)
        if status is not None:
            stmt = stmt.where(AutomationJob.status == status)

        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            stmt.order_by(
                AutomationJob.created_at.desc(),
                AutomationJob.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().unique().all(), total

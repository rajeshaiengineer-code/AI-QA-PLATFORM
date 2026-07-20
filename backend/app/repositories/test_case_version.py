"""
Test Case Version Repository

Async data-access for TestCaseVersion snapshots.
"""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.models.test_case_version import TestCaseVersion
from app.repositories.base import BaseRepository


class TestCaseVersionRepository(BaseRepository[TestCaseVersion]):
    """Repository for TestCaseVersion history."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TestCaseVersion)

    def _base_query(self) -> Select:
        return (
            select(TestCaseVersion)
            .options(noload(TestCaseVersion.test_case))
            .where(TestCaseVersion.is_deleted.is_(False))
        )

    async def max_version_number(self, test_case_id: UUID) -> int:
        """Return the highest version_number for a test case (or 0 if none)."""
        stmt = select(func.max(TestCaseVersion.version_number)).where(
            TestCaseVersion.test_case_id == test_case_id,
            TestCaseVersion.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        value = result.scalar_one_or_none()
        return int(value) if value is not None else 0

    async def list_for_test_case(
        self,
        test_case_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[Sequence[TestCaseVersion], int]:
        """List version history newest-first with pagination."""
        stmt = self._base_query().where(TestCaseVersion.test_case_id == test_case_id)
        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            stmt.order_by(TestCaseVersion.version_number.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def get_by_id(
        self,
        entity_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Optional[TestCaseVersion]:
        stmt = (
            select(TestCaseVersion)
            .options(noload(TestCaseVersion.test_case))
            .where(TestCaseVersion.id == entity_id)
        )
        if not include_deleted:
            stmt = stmt.where(TestCaseVersion.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

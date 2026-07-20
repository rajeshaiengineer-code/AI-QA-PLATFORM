"""
Test Case Repository

Async data-access for TestCase entities.
"""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.models.enums import TestCaseCategory, TestCaseSource, TestCaseStatus
from app.models.test_case import TestCase
from app.repositories.base import BaseRepository


class TestCaseRepository(BaseRepository[TestCase]):
    """Repository for TestCase CRUD and story-scoped listing."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TestCase)

    def _base_query(self) -> Select:
        return (
            select(TestCase)
            .options(
                noload(TestCase.story),
                noload(TestCase.acceptance_criteria),
                noload(TestCase.executions),
                noload(TestCase.bugs),
                noload(TestCase.versions),
            )
            .where(TestCase.is_deleted.is_(False))
        )

    async def get_by_id(
        self,
        entity_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Optional[TestCase]:
        stmt = (
            select(TestCase)
            .options(
                noload(TestCase.story),
                noload(TestCase.acceptance_criteria),
                noload(TestCase.executions),
                noload(TestCase.bugs),
                noload(TestCase.versions),
            )
            .where(TestCase.id == entity_id)
        )
        if not include_deleted:
            stmt = stmt.where(TestCase.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_story(
        self,
        story_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
        category: Optional[TestCaseCategory] = None,
        source: Optional[TestCaseSource] = None,
        status: Optional[TestCaseStatus] = None,
    ) -> tuple[Sequence[TestCase], int]:
        """List test cases for a story with optional filters and pagination."""
        stmt = self._base_query().where(TestCase.story_id == story_id)
        if category is not None:
            stmt = stmt.where(TestCase.category == category.value)
        if source is not None:
            stmt = stmt.where(TestCase.source == source.value)
        if status is not None:
            stmt = stmt.where(TestCase.status == status.value)

        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = (
            stmt.order_by(TestCase.order_index.asc(), TestCase.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def list_all_for_story(self, story_id: UUID) -> Sequence[TestCase]:
        """Return all non-deleted test cases for a story (no pagination)."""
        stmt = (
            self._base_query()
            .where(TestCase.story_id == story_id)
            .order_by(TestCase.order_index.asc(), TestCase.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_for_story_by_statuses(
        self,
        story_id: UUID,
        statuses: Sequence[TestCaseStatus],
    ) -> Sequence[TestCase]:
        """Return non-deleted test cases matching any of the given statuses."""
        if not statuses:
            return []
        status_values = [s.value for s in statuses]
        stmt = (
            self._base_query()
            .where(
                TestCase.story_id == story_id,
                TestCase.status.in_(status_values),
            )
            .order_by(TestCase.order_index.asc(), TestCase.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_status(
        self,
        story_id: UUID,
        status: TestCaseStatus,
    ) -> int:
        """Count non-deleted test cases for a story with the given status."""
        stmt = select(func.count()).where(
            TestCase.story_id == story_id,
            TestCase.is_deleted.is_(False),
            TestCase.status == status.value,
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def count_for_story(self, story_id: UUID) -> int:
        """Count all non-deleted test cases for a story."""
        stmt = select(func.count()).where(
            TestCase.story_id == story_id,
            TestCase.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def max_order_index(self, story_id: UUID) -> int:
        """Return the highest order_index for a story (or -1 if none)."""
        stmt = select(func.max(TestCase.order_index)).where(
            TestCase.story_id == story_id,
            TestCase.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        value = result.scalar_one_or_none()
        return int(value) if value is not None else -1

    async def add_many(self, entities: Sequence[TestCase]) -> Sequence[TestCase]:
        """Persist multiple test cases and refresh column values."""
        for entity in entities:
            self.session.add(entity)
        await self.session.flush()
        for entity in entities:
            column_keys = [column.key for column in entity.__table__.columns]
            await self.session.refresh(entity, attribute_names=column_keys)
        return entities

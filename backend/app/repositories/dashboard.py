"""
Dashboard Repository

Aggregate read queries for reporting APIs (org/project scoped).
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automation_artifact import AutomationArtifact
from app.models.automation_job import AutomationJob
from app.models.bdd_feature import BddFeature
from app.models.enums import TestCaseSource, TestCaseStatus
from app.models.execution import Execution
from app.models.project import Project
from app.models.sprint import Sprint
from app.models.story import Story
from app.models.story_analysis import StoryAnalysis
from app.models.test_case import TestCase


class DashboardRepository:
    """Read-only aggregates for dashboard endpoints."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def _project_ids_subquery(
        self,
        *,
        organization_id: Optional[UUID],
        project_id: Optional[UUID],
    ) -> Optional[Select]:
        """Return a project-id select when scoping is needed; None = no filter."""
        if project_id is not None:
            return select(Project.id).where(
                Project.id == project_id,
                Project.is_deleted.is_(False),
            )
        if organization_id is not None:
            return select(Project.id).where(
                Project.organization_id == organization_id,
                Project.is_deleted.is_(False),
            )
        return None

    async def resolve_project_ids(
        self,
        *,
        organization_id: Optional[UUID],
        project_id: Optional[UUID],
    ) -> Optional[List[UUID]]:
        """
        Resolve scoped project IDs.

        Returns:
            None — no org/project filter (platform-wide)
            [] — scope resolved to zero projects
            [uuid, ...] — explicit project list
        """
        subq = self._project_ids_subquery(
            organization_id=organization_id,
            project_id=project_id,
        )
        if subq is None:
            return None
        result = await self.session.execute(subq)
        return list(result.scalars().all())

    async def count_projects(
        self,
        *,
        organization_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
    ) -> int:
        stmt = select(func.count()).select_from(Project).where(
            Project.is_deleted.is_(False)
        )
        if project_id is not None:
            stmt = stmt.where(Project.id == project_id)
        elif organization_id is not None:
            stmt = stmt.where(Project.organization_id == organization_id)
        return int(await self.session.scalar(stmt) or 0)

    async def count_sprints(self, project_ids: Optional[List[UUID]]) -> int:
        stmt = select(func.count()).select_from(Sprint).where(
            Sprint.is_deleted.is_(False)
        )
        if project_ids is not None:
            if not project_ids:
                return 0
            stmt = stmt.where(Sprint.project_id.in_(project_ids))
        return int(await self.session.scalar(stmt) or 0)

    async def count_stories(self, project_ids: Optional[List[UUID]]) -> int:
        stmt = select(func.count()).select_from(Story).where(
            Story.is_deleted.is_(False)
        )
        if project_ids is not None:
            if not project_ids:
                return 0
            stmt = stmt.where(Story.project_id.in_(project_ids))
        return int(await self.session.scalar(stmt) or 0)

    async def stories_by_status(
        self,
        project_ids: Optional[List[UUID]],
    ) -> Dict[str, int]:
        stmt = (
            select(Story.status, func.count())
            .where(Story.is_deleted.is_(False))
            .group_by(Story.status)
        )
        if project_ids is not None:
            if not project_ids:
                return {}
            stmt = stmt.where(Story.project_id.in_(project_ids))
        rows = await self.session.execute(stmt)
        out: Dict[str, int] = {}
        for status, count in rows.all():
            key = status.value if hasattr(status, "value") else str(status)
            out[key] = int(count)
        return out

    async def count_test_cases(self, project_ids: Optional[List[UUID]]) -> int:
        stmt = (
            select(func.count())
            .select_from(TestCase)
            .join(Story, Story.id == TestCase.story_id)
            .where(
                TestCase.is_deleted.is_(False),
                Story.is_deleted.is_(False),
            )
        )
        if project_ids is not None:
            if not project_ids:
                return 0
            stmt = stmt.where(Story.project_id.in_(project_ids))
        return int(await self.session.scalar(stmt) or 0)

    async def count_automation_jobs(
        self,
        project_ids: Optional[List[UUID]],
    ) -> int:
        stmt = select(func.count()).select_from(AutomationJob).where(
            AutomationJob.is_deleted.is_(False)
        )
        if project_ids is not None:
            if not project_ids:
                return 0
            stmt = stmt.where(AutomationJob.project_id.in_(project_ids))
        return int(await self.session.scalar(stmt) or 0)

    async def count_executions(self, project_ids: Optional[List[UUID]]) -> int:
        stmt = (
            select(func.count())
            .select_from(Execution)
            .join(AutomationJob, AutomationJob.id == Execution.automation_job_id)
            .where(
                Execution.is_deleted.is_(False),
                AutomationJob.is_deleted.is_(False),
            )
        )
        if project_ids is not None:
            if not project_ids:
                return 0
            stmt = stmt.where(AutomationJob.project_id.in_(project_ids))
        return int(await self.session.scalar(stmt) or 0)

    async def executions_by_status(
        self,
        project_ids: Optional[List[UUID]],
    ) -> Dict[str, int]:
        stmt = (
            select(Execution.status, func.count())
            .select_from(Execution)
            .join(AutomationJob, AutomationJob.id == Execution.automation_job_id)
            .where(
                Execution.is_deleted.is_(False),
                AutomationJob.is_deleted.is_(False),
            )
            .group_by(Execution.status)
        )
        if project_ids is not None:
            if not project_ids:
                return {}
            stmt = stmt.where(AutomationJob.project_id.in_(project_ids))
        rows = await self.session.execute(stmt)
        out: Dict[str, int] = {}
        for status, count in rows.all():
            key = status.value if hasattr(status, "value") else str(status)
            out[key] = int(count)
        return out

    async def list_execution_status_timestamps(
        self,
        *,
        project_ids: Optional[List[UUID]],
        from_dt: datetime,
        to_dt: datetime,
    ) -> Sequence[Tuple[datetime, str]]:
        """Return (created_at, status) for executions in the window."""
        stmt = (
            select(Execution.created_at, Execution.status)
            .select_from(Execution)
            .join(AutomationJob, AutomationJob.id == Execution.automation_job_id)
            .where(
                Execution.is_deleted.is_(False),
                AutomationJob.is_deleted.is_(False),
                Execution.created_at >= from_dt,
                Execution.created_at <= to_dt,
            )
            .order_by(Execution.created_at.asc())
        )
        if project_ids is not None:
            if not project_ids:
                return []
            stmt = stmt.where(AutomationJob.project_id.in_(project_ids))
        rows = await self.session.execute(stmt)
        result: List[Tuple[datetime, str]] = []
        for created_at, status in rows.all():
            key = status.value if hasattr(status, "value") else str(status)
            result.append((created_at, key))
        return result

    async def coverage_counts(
        self,
        project_ids: Optional[List[UUID]],
    ) -> Dict[str, int]:
        """Story coverage + test-case status breakdown."""
        if project_ids is not None and not project_ids:
            return {
                "stories_total": 0,
                "stories_with_test_cases": 0,
                "test_cases_total": 0,
                "test_cases_approved": 0,
                "test_cases_pending_review": 0,
                "test_cases_draft": 0,
                "test_cases_rejected": 0,
            }

        stories_stmt = select(func.count()).select_from(Story).where(
            Story.is_deleted.is_(False)
        )
        if project_ids is not None:
            stories_stmt = stories_stmt.where(Story.project_id.in_(project_ids))
        stories_total = int(await self.session.scalar(stories_stmt) or 0)

        with_tc_stmt = (
            select(func.count(func.distinct(TestCase.story_id)))
            .select_from(TestCase)
            .join(Story, Story.id == TestCase.story_id)
            .where(
                TestCase.is_deleted.is_(False),
                Story.is_deleted.is_(False),
            )
        )
        if project_ids is not None:
            with_tc_stmt = with_tc_stmt.where(Story.project_id.in_(project_ids))
        stories_with = int(await self.session.scalar(with_tc_stmt) or 0)

        status_stmt = (
            select(TestCase.status, func.count())
            .select_from(TestCase)
            .join(Story, Story.id == TestCase.story_id)
            .where(
                TestCase.is_deleted.is_(False),
                Story.is_deleted.is_(False),
            )
            .group_by(TestCase.status)
        )
        if project_ids is not None:
            status_stmt = status_stmt.where(Story.project_id.in_(project_ids))
        status_rows = await self.session.execute(status_stmt)
        by_status: Dict[str, int] = {}
        total_tc = 0
        for status, count in status_rows.all():
            key = status.value if hasattr(status, "value") else str(status)
            by_status[key] = int(count)
            total_tc += int(count)

        return {
            "stories_total": stories_total,
            "stories_with_test_cases": stories_with,
            "test_cases_total": total_tc,
            "test_cases_approved": by_status.get(TestCaseStatus.APPROVED.value, 0),
            "test_cases_pending_review": by_status.get(
                TestCaseStatus.PENDING_REVIEW.value, 0
            ),
            "test_cases_draft": by_status.get(TestCaseStatus.DRAFT.value, 0),
            "test_cases_rejected": by_status.get(TestCaseStatus.REJECTED.value, 0),
        }

    async def count_analyses(self, project_ids: Optional[List[UUID]]) -> int:
        stmt = (
            select(func.count())
            .select_from(StoryAnalysis)
            .join(Story, Story.id == StoryAnalysis.story_id)
            .where(
                StoryAnalysis.is_deleted.is_(False),
                Story.is_deleted.is_(False),
            )
        )
        if project_ids is not None:
            if not project_ids:
                return 0
            stmt = stmt.where(Story.project_id.in_(project_ids))
        return int(await self.session.scalar(stmt) or 0)

    async def count_ai_test_cases(self, project_ids: Optional[List[UUID]]) -> int:
        stmt = (
            select(func.count())
            .select_from(TestCase)
            .join(Story, Story.id == TestCase.story_id)
            .where(
                TestCase.is_deleted.is_(False),
                Story.is_deleted.is_(False),
                TestCase.source == TestCaseSource.AI.value,
            )
        )
        if project_ids is not None:
            if not project_ids:
                return 0
            stmt = stmt.where(Story.project_id.in_(project_ids))
        return int(await self.session.scalar(stmt) or 0)

    async def count_bdd_artifacts(self, project_ids: Optional[List[UUID]]) -> int:
        stmt = (
            select(func.count())
            .select_from(BddFeature)
            .join(Story, Story.id == BddFeature.story_id)
            .where(
                BddFeature.is_deleted.is_(False),
                Story.is_deleted.is_(False),
            )
        )
        if project_ids is not None:
            if not project_ids:
                return 0
            stmt = stmt.where(Story.project_id.in_(project_ids))
        return int(await self.session.scalar(stmt) or 0)

    async def count_playwright_artifacts(
        self,
        project_ids: Optional[List[UUID]],
    ) -> int:
        stmt = (
            select(func.count())
            .select_from(AutomationArtifact)
            .join(Story, Story.id == AutomationArtifact.story_id)
            .where(
                AutomationArtifact.is_deleted.is_(False),
                Story.is_deleted.is_(False),
            )
        )
        if project_ids is not None:
            if not project_ids:
                return 0
            stmt = stmt.where(Story.project_id.in_(project_ids))
        return int(await self.session.scalar(stmt) or 0)

    async def organization_exists(self, organization_id: UUID) -> bool:
        from app.models.organization import Organization

        stmt = select(Organization.id).where(
            Organization.id == organization_id,
            Organization.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def project_exists(self, project_id: UUID) -> bool:
        stmt = select(Project.id).where(
            Project.id == project_id,
            Project.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def project_belongs_to_org(
        self,
        project_id: UUID,
        organization_id: UUID,
    ) -> bool:
        stmt = select(Project.id).where(
            Project.id == project_id,
            Project.organization_id == organization_id,
            Project.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

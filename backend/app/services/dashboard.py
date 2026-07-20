"""
Dashboard Service

Business orchestration for reporting aggregates.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.repositories.dashboard import DashboardRepository
from app.schemas.dashboard import (
    AiMetricsResponse,
    CoverageResponse,
    DashboardScope,
    DashboardSummaryResponse,
    ExecutionTrendBucket,
    ExecutionTrendsResponse,
)


class DashboardService:
    """Service layer for dashboard & reporting APIs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = DashboardRepository(session)

    async def _resolve_scope(
        self,
        *,
        organization_id: Optional[UUID],
        project_id: Optional[UUID],
    ) -> Tuple[DashboardScope, Optional[List[UUID]]]:
        if organization_id is not None:
            if not await self.repository.organization_exists(organization_id):
                raise NotFoundException("Organization", str(organization_id))
        if project_id is not None:
            if not await self.repository.project_exists(project_id):
                raise NotFoundException("Project", str(project_id))
            if organization_id is not None:
                belongs = await self.repository.project_belongs_to_org(
                    project_id,
                    organization_id,
                )
                if not belongs:
                    raise BadRequestException(
                        "Project does not belong to the specified organization"
                    )

        project_ids = await self.repository.resolve_project_ids(
            organization_id=organization_id,
            project_id=project_id,
        )
        scope = DashboardScope(
            organization_id=organization_id,
            project_id=project_id,
        )
        return scope, project_ids

    async def get_summary(
        self,
        *,
        organization_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
    ) -> DashboardSummaryResponse:
        scope, project_ids = await self._resolve_scope(
            organization_id=organization_id,
            project_id=project_id,
        )
        return DashboardSummaryResponse(
            scope=scope,
            project_count=await self.repository.count_projects(
                organization_id=organization_id,
                project_id=project_id,
            ),
            sprint_count=await self.repository.count_sprints(project_ids),
            story_count=await self.repository.count_stories(project_ids),
            test_case_count=await self.repository.count_test_cases(project_ids),
            execution_count=await self.repository.count_executions(project_ids),
            automation_job_count=await self.repository.count_automation_jobs(
                project_ids
            ),
            executions_by_status=await self.repository.executions_by_status(
                project_ids
            ),
            stories_by_status=await self.repository.stories_by_status(project_ids),
        )

    async def get_execution_trends(
        self,
        *,
        organization_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        days: int = 30,
        bucket: str = "day",
    ) -> ExecutionTrendsResponse:
        if days < 1 or days > 365:
            raise BadRequestException("days must be between 1 and 365")
        bucket_norm = bucket.strip().lower()
        if bucket_norm not in {"day", "week"}:
            raise BadRequestException("bucket must be 'day' or 'week'")

        scope, project_ids = await self._resolve_scope(
            organization_id=organization_id,
            project_id=project_id,
        )

        now = datetime.now(timezone.utc)
        # Inclusive window: last N calendar days ending now
        from_dt = (now - timedelta(days=days - 1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        to_dt = now

        rows = await self.repository.list_execution_status_timestamps(
            project_ids=project_ids,
            from_dt=from_dt,
            to_dt=to_dt,
        )
        buckets = self._build_trend_buckets(
            rows=rows,
            from_dt=from_dt,
            to_dt=to_dt,
            bucket=bucket_norm,
        )
        return ExecutionTrendsResponse(
            scope=scope,
            days=days,
            bucket=bucket_norm,
            from_date=from_dt,
            to_date=to_dt,
            buckets=buckets,
        )

    def _build_trend_buckets(
        self,
        *,
        rows: List[Tuple[datetime, str]],
        from_dt: datetime,
        to_dt: datetime,
        bucket: str,
    ) -> List[ExecutionTrendBucket]:
        # Seed empty buckets covering the full window
        seeded: Dict[date, ExecutionTrendBucket] = {}
        cursor = from_dt.date()
        end = to_dt.date()
        step = timedelta(days=7 if bucket == "week" else 1)

        if bucket == "week":
            # Align to Monday of the week containing from_dt
            cursor = cursor - timedelta(days=cursor.weekday())

        while cursor <= end:
            label = (
                cursor.isoformat()
                if bucket == "day"
                else f"week-{cursor.isocalendar()[0]}-W{cursor.isocalendar()[1]:02d}"
            )
            seeded[cursor] = ExecutionTrendBucket(
                bucket_start=cursor,
                bucket_label=label,
            )
            cursor = cursor + step

        def bucket_key(dt: datetime) -> date:
            d = dt.date() if dt.tzinfo is None else dt.astimezone(timezone.utc).date()
            if bucket == "day":
                return d
            return d - timedelta(days=d.weekday())

        for created_at, status in rows:
            if created_at is None:
                continue
            key = bucket_key(created_at)
            if key not in seeded:
                # Execution outside seeded window edge — skip
                continue
            item = seeded[key]
            item.total += 1
            if status == "passed":
                item.passed += 1
            elif status == "failed":
                item.failed += 1
            elif status == "error":
                item.error += 1
            elif status == "skipped":
                item.skipped += 1
            else:
                item.other += 1

        return sorted(seeded.values(), key=lambda b: b.bucket_start)

    async def get_coverage(
        self,
        *,
        organization_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
    ) -> CoverageResponse:
        scope, project_ids = await self._resolve_scope(
            organization_id=organization_id,
            project_id=project_id,
        )
        counts = await self.repository.coverage_counts(project_ids)
        stories_total = counts["stories_total"]
        stories_with = counts["stories_with_test_cases"]
        stories_without = max(stories_total - stories_with, 0)
        tc_total = counts["test_cases_total"]
        approved = counts["test_cases_approved"]

        coverage_ratio = (
            round(stories_with / stories_total, 4) if stories_total > 0 else 0.0
        )
        approved_ratio = round(approved / tc_total, 4) if tc_total > 0 else 0.0

        return CoverageResponse(
            scope=scope,
            stories_total=stories_total,
            stories_with_test_cases=stories_with,
            stories_without_test_cases=stories_without,
            test_cases_total=tc_total,
            test_cases_approved=approved,
            test_cases_pending_review=counts["test_cases_pending_review"],
            test_cases_draft=counts["test_cases_draft"],
            test_cases_rejected=counts["test_cases_rejected"],
            approved_ratio=approved_ratio,
            coverage_ratio=coverage_ratio,
        )

    async def get_ai_metrics(
        self,
        *,
        organization_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
    ) -> AiMetricsResponse:
        scope, project_ids = await self._resolve_scope(
            organization_id=organization_id,
            project_id=project_id,
        )
        return AiMetricsResponse(
            scope=scope,
            analyses_count=await self.repository.count_analyses(project_ids),
            generated_test_cases=await self.repository.count_ai_test_cases(
                project_ids
            ),
            bdd_artifacts=await self.repository.count_bdd_artifacts(project_ids),
            playwright_artifacts=await self.repository.count_playwright_artifacts(
                project_ids
            ),
        )

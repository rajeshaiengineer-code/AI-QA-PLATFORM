"""
Dashboard reporting schemas.

Aggregate stats for org/project-scoped dashboards (no charting payloads).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import Field

from app.schemas.base import BaseSchema


class DashboardScope(BaseSchema):
    """Echo of applied org/project filters."""

    organization_id: Optional[UUID] = None
    project_id: Optional[UUID] = None


class DashboardSummaryResponse(BaseSchema):
    """Org/project scoped entity counts."""

    scope: DashboardScope
    project_count: int = 0
    sprint_count: int = 0
    story_count: int = 0
    test_case_count: int = 0
    execution_count: int = 0
    automation_job_count: int = 0
    executions_by_status: Dict[str, int] = Field(default_factory=dict)
    stories_by_status: Dict[str, int] = Field(default_factory=dict)


class ExecutionTrendBucket(BaseSchema):
    """One time-series bucket of execution outcomes."""

    bucket_start: date
    bucket_label: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    error: int = 0
    skipped: int = 0
    other: int = 0


class ExecutionTrendsResponse(BaseSchema):
    """Execution counts grouped into day or week buckets."""

    scope: DashboardScope
    days: int
    bucket: str
    from_date: datetime
    to_date: datetime
    buckets: List[ExecutionTrendBucket] = Field(default_factory=list)


class CoverageResponse(BaseSchema):
    """Story ↔ test-case coverage and approval ratios."""

    scope: DashboardScope
    stories_total: int = 0
    stories_with_test_cases: int = 0
    stories_without_test_cases: int = 0
    test_cases_total: int = 0
    test_cases_approved: int = 0
    test_cases_pending_review: int = 0
    test_cases_draft: int = 0
    test_cases_rejected: int = 0
    approved_ratio: float = 0.0
    coverage_ratio: float = 0.0


class AiMetricsResponse(BaseSchema):
    """AI pipeline artifact counts."""

    scope: DashboardScope
    analyses_count: int = 0
    generated_test_cases: int = 0
    bdd_artifacts: int = 0
    playwright_artifacts: int = 0

"""
Execution Engine Service

Runs a stub/local test runner against resolved test cases, persists
AutomationJob + Execution rows, supports retry, and optionally emits
workflow ExecutionStarted / ExecutionCompleted events.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.core.exceptions import BadRequestException, NotFoundException
from app.execution.factory import TestRunner, get_runner
from app.execution.playwright_runner import collect_playwright_files
from app.execution.stub_runner import CaseRunResult, StubTestRunner
from app.models.automation_artifact import AutomationArtifact
from app.models.automation_job import AutomationJob
from app.models.enums import AutomationStatus, ExecutionStatus, TestCaseStatus
from app.models.execution import Execution
from app.models.story import Story
from app.models.test_case import TestCase
from app.repositories.automation_artifact import AutomationArtifactRepository
from app.repositories.automation_job import AutomationJobRepository
from app.repositories.execution import ExecutionRepository
from app.repositories.story import StoryRepository
from app.repositories.test_case import TestCaseRepository
from app.schemas.base import PaginatedResponse
from app.schemas.execution import (
    AutomationJobResponse,
    AutomationJobSummary,
    ExecutionDetailResponse,
    ExecutionResponse,
    ExecutionRunRequest,
    ExecutionRunResponse,
)


class ExecutionEngineService:
    """Business orchestration for stub or local Playwright execution."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        runner: Optional[TestRunner] = None,
    ) -> None:
        self.session = session
        self.runner: TestRunner = runner or StubTestRunner()
        self.job_repo = AutomationJobRepository(session)
        self.execution_repo = ExecutionRepository(session)
        self.story_repo = StoryRepository(session)
        self.test_case_repo = TestCaseRepository(session)
        self.artifact_repo = AutomationArtifactRepository(session)

    async def run(self, request: ExecutionRunRequest) -> ExecutionRunResponse:
        """Resolve targets, create/run a job, persist results, emit workflow."""
        runner_name = request.runner or (request.config or {}).get("runner") or "stub"
        self.runner = get_runner(str(runner_name))

        project_id, sprint_id, cases, config, job_name, existing_job = (
            await self._resolve_run_target(request)
        )
        await self._attach_playwright_files(config)

        if existing_job is not None and existing_job.status in (
            AutomationStatus.PENDING,
            AutomationStatus.QUEUED,
        ):
            job = existing_job
            if not job.executions:
                await self._create_pending_executions(job, cases)
            else:
                cases = await self._cases_from_job(job)
        else:
            job = AutomationJob(
                project_id=project_id,
                sprint_id=sprint_id,
                name=job_name,
                status=AutomationStatus.PENDING,
                config=config,
            )
            await self.job_repo.add(job)
            await self._create_pending_executions(job, cases)

        workflow_run_id = request.workflow_run_id
        if workflow_run_id is not None:
            await self._emit_workflow_started(workflow_run_id, job)

        try:
            job_view = await self._execute_job(job, cases, config)
        except Exception as exc:
            if workflow_run_id is not None:
                await self._emit_workflow_failed_to_start(
                    workflow_run_id, job, str(exc)
                )
            raise

        if workflow_run_id is not None:
            await self._emit_workflow_completed(workflow_run_id, job_view)

        return ExecutionRunResponse(
            job=job_view,
            workflow_run_id=workflow_run_id,
            runner=self.runner.name,
        )

    async def retry_execution(self, execution_id: UUID) -> ExecutionDetailResponse:
        """Re-run a failed/error execution in place and bump retry_count."""
        execution = await self.execution_repo.get_by_id(execution_id)
        if execution is None:
            raise NotFoundException("Execution", str(execution_id))

        if execution.status not in (
            ExecutionStatus.FAILED,
            ExecutionStatus.ERROR,
            ExecutionStatus.BLOCKED,
        ):
            raise BadRequestException(
                f"Only failed/error/blocked executions can be retried "
                f"(current={execution.status.value})"
            )

        test_case = await self._get_test_case(execution.test_case_id)
        job = execution.automation_job
        config = dict(job.config or {}) if job is not None else {}
        self.runner = get_runner(str(config.get("runner") or "stub"))
        await self._attach_playwright_files(config)

        now = datetime.now(timezone.utc)
        execution.status = ExecutionStatus.RUNNING
        execution.started_at = now
        execution.completed_at = None
        execution.duration_ms = None
        execution.error_message = None
        execution.stack_trace = None
        execution.evidence_url = None
        execution.retry_count = int(execution.retry_count or 0) + 1
        await self.session.flush()

        results = self.runner.run([test_case], config=config)
        result = results[0]
        self._apply_case_result(execution, result, started_at=now)
        await self.session.flush()

        if job is not None:
            await self._refresh_job_aggregate_status(job)

        return await self.get_execution(execution.id)

    async def get_execution(self, execution_id: UUID) -> ExecutionDetailResponse:
        execution = await self.execution_repo.get_by_id(execution_id)
        if execution is None:
            raise NotFoundException("Execution", str(execution_id))
        base = ExecutionResponse.model_validate(execution)
        job_summary = None
        if execution.automation_job is not None:
            job_summary = AutomationJobSummary.model_validate(
                execution.automation_job
            )
        return ExecutionDetailResponse(
            **base.model_dump(),
            automation_job=job_summary,
        )

    async def list_executions(
        self,
        *,
        automation_job_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        story_id: Optional[UUID] = None,
        status: Optional[ExecutionStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[ExecutionResponse]:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)
        offset = (page - 1) * page_size
        rows, total = await self.execution_repo.list_executions(
            automation_job_id=automation_job_id,
            project_id=project_id,
            story_id=story_id,
            status=status,
            offset=offset,
            limit=page_size,
        )
        items = [ExecutionResponse.model_validate(row) for row in rows]
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_job(self, job_id: UUID) -> AutomationJobResponse:
        job = await self.job_repo.get_by_id(job_id)
        if job is None:
            raise NotFoundException("AutomationJob", str(job_id))
        return self._job_response(job)

    # ------------------------------------------------------------------
    # Resolve targets
    # ------------------------------------------------------------------

    async def _resolve_run_target(
        self,
        request: ExecutionRunRequest,
    ) -> Tuple[
        UUID,
        Optional[UUID],
        Sequence[TestCase],
        Dict[str, Any],
        str,
        Optional[AutomationJob],
    ]:
        config: Dict[str, Any] = dict(request.config or {})
        if request.force_fail_test_case_ids:
            config["force_fail_test_case_ids"] = [
                str(x) for x in request.force_fail_test_case_ids
            ]
        config["runner"] = self.runner.name

        if request.story_id is not None:
            story = await self._get_story(request.story_id)
            cases = await self._list_cases_for_story(
                story.id, include_drafts=request.include_drafts
            )
            if not cases:
                raise BadRequestException(
                    f"No executable test cases found for story {story.id}"
                )
            config["story_id"] = str(story.id)
            # Prefer newest Playwright artifact for this story when running PW
            if self.runner.name == "playwright" and not config.get(
                "automation_artifact_id"
            ):
                latest = await self.artifact_repo.get_latest_for_story(story.id)
                if latest is not None:
                    config["automation_artifact_id"] = str(latest.id)
            name = request.name or f"Execution — {story.title[:80]}"
            return story.project_id, story.sprint_id, cases, config, name, None

        if request.automation_artifact_id is not None:
            artifact = await self._get_artifact(request.automation_artifact_id)
            story = await self._get_story(artifact.story_id)
            cases = await self._cases_from_artifact(
                artifact, include_drafts=request.include_drafts
            )
            if not cases:
                raise BadRequestException(
                    f"No executable test cases found for artifact {artifact.id}"
                )
            config["story_id"] = str(story.id)
            config["automation_artifact_id"] = str(artifact.id)
            name = request.name or f"Execution — {artifact.name[:80]}"
            return story.project_id, story.sprint_id, cases, config, name, None

        assert request.automation_job_id is not None
        job = await self.job_repo.get_by_id(request.automation_job_id)
        if job is None:
            raise NotFoundException("AutomationJob", str(request.automation_job_id))
        cases = await self._cases_from_job(job)
        if not cases:
            raise BadRequestException(
                f"AutomationJob {job.id} has no linked test cases to run"
            )
        merged = dict(job.config or {})
        merged.update(config)
        if request.workflow_run_id:
            merged["workflow_run_id"] = str(request.workflow_run_id)
        name = request.name or job.name
        if job.status in (AutomationStatus.PENDING, AutomationStatus.QUEUED):
            job.config = merged
            await self.session.flush()
            return job.project_id, job.sprint_id, cases, merged, name, job
        # Completed/failed/cancelled/running → spawn a fresh job
        return job.project_id, job.sprint_id, cases, merged, name, None

    async def _cases_from_artifact(
        self,
        artifact: AutomationArtifact,
        *,
        include_drafts: bool,
    ) -> Sequence[TestCase]:
        source_ids = artifact.source_test_case_ids or []
        if source_ids:
            cases: List[TestCase] = []
            for raw in source_ids:
                tc = await self._get_test_case(UUID(str(raw)))
                if include_drafts or tc.status == TestCaseStatus.APPROVED.value:
                    cases.append(tc)
            if cases:
                return cases
        return await self._list_cases_for_story(
            artifact.story_id, include_drafts=include_drafts
        )

    async def _cases_from_job(self, job: AutomationJob) -> Sequence[TestCase]:
        executions = list(job.executions or [])
        if executions:
            cases: List[TestCase] = []
            for ex in executions:
                cases.append(await self._get_test_case(ex.test_case_id))
            return cases
        cfg = job.config or {}
        raw_ids = cfg.get("test_case_ids") or []
        cases = []
        for raw in raw_ids:
            cases.append(await self._get_test_case(UUID(str(raw))))
        if cases:
            return cases
        story_raw = cfg.get("story_id")
        if story_raw:
            return await self._list_cases_for_story(
                UUID(str(story_raw)), include_drafts=True
            )
        return []

    async def _list_cases_for_story(
        self,
        story_id: UUID,
        *,
        include_drafts: bool,
    ) -> Sequence[TestCase]:
        if include_drafts:
            return list(await self.test_case_repo.list_all_for_story(story_id))
        return list(
            await self.test_case_repo.list_for_story_by_statuses(
                story_id,
                [TestCaseStatus.APPROVED],
            )
        )

    # ------------------------------------------------------------------
    # Playwright helpers
    # ------------------------------------------------------------------

    async def _attach_playwright_files(self, config: Dict[str, Any]) -> None:
        """Load generated artifact files into config for the Playwright runner."""
        if self.runner.name != "playwright":
            return
        if config.get("playwright_files"):
            return
        raw_id = config.get("automation_artifact_id")
        artifact: Optional[AutomationArtifact] = None
        if raw_id:
            artifact = await self._get_artifact(UUID(str(raw_id)))
        elif config.get("story_id"):
            artifact = await self.artifact_repo.get_latest_for_story(
                UUID(str(config["story_id"]))
            )
            if artifact is not None:
                config["automation_artifact_id"] = str(artifact.id)
        if artifact is None:
            return
        files = collect_playwright_files(artifact)
        if files:
            config["playwright_files"] = files

    # ------------------------------------------------------------------
    # Execute
    # ------------------------------------------------------------------

    async def _create_pending_executions(
        self,
        job: AutomationJob,
        cases: Sequence[TestCase],
    ) -> None:
        cfg = dict(job.config or {})
        cfg["test_case_ids"] = [str(c.id) for c in cases]
        job.config = cfg
        for case in cases:
            self.session.add(
                Execution(
                    automation_job_id=job.id,
                    test_case_id=case.id,
                    status=ExecutionStatus.PENDING,
                )
            )
        await self.session.flush()
        # Reload executions on job
        refreshed = await self.job_repo.get_by_id(job.id)
        if refreshed is not None:
            job.executions = list(refreshed.executions or [])

    async def _execute_job(
        self,
        job: AutomationJob,
        cases: Sequence[TestCase],
        config: Dict[str, Any],
    ) -> AutomationJobResponse:
        now = datetime.now(timezone.utc)
        job.status = AutomationStatus.RUNNING
        job.started_at = now
        job.error_message = None
        await self.session.flush()

        executions = await self.execution_repo.list_for_job(job.id)
        by_case = {ex.test_case_id: ex for ex in executions}

        for ex in executions:
            ex.status = ExecutionStatus.RUNNING
            ex.started_at = now
        await self.session.flush()

        results = self.runner.run(cases, config=config)
        for result in results:
            ex = by_case.get(result.test_case_id)
            if ex is None:
                continue
            self._apply_case_result(ex, result, started_at=now)

        await self._refresh_job_aggregate_status(job)
        refreshed = await self.job_repo.get_by_id(job.id)
        assert refreshed is not None
        return self._job_response(refreshed)

    def _apply_case_result(
        self,
        execution: Execution,
        result: CaseRunResult,
        *,
        started_at: datetime,
    ) -> None:
        completed = datetime.now(timezone.utc)
        execution.status = result.status
        execution.started_at = started_at
        execution.completed_at = completed
        execution.duration_ms = result.duration_ms
        execution.error_message = result.error_message
        execution.stack_trace = result.stack_trace
        execution.evidence_url = result.evidence_url

    async def _refresh_job_aggregate_status(self, job: AutomationJob) -> None:
        executions = await self.execution_repo.list_for_job(job.id)
        statuses = [ex.status for ex in executions]
        completed = datetime.now(timezone.utc)
        job.completed_at = completed

        if not statuses:
            job.status = AutomationStatus.FAILED
            job.error_message = "No executions recorded"
            await self.session.flush()
            return

        if any(s == ExecutionStatus.RUNNING for s in statuses):
            job.status = AutomationStatus.RUNNING
            job.completed_at = None
        elif any(s == ExecutionStatus.PENDING for s in statuses):
            job.status = AutomationStatus.QUEUED
            job.completed_at = None
        elif any(
            s in (ExecutionStatus.FAILED, ExecutionStatus.ERROR, ExecutionStatus.BLOCKED)
            for s in statuses
        ):
            job.status = AutomationStatus.FAILED
            failed_n = sum(
                1
                for s in statuses
                if s
                in (
                    ExecutionStatus.FAILED,
                    ExecutionStatus.ERROR,
                    ExecutionStatus.BLOCKED,
                )
            )
            job.error_message = f"{failed_n} execution(s) failed"
        else:
            job.status = AutomationStatus.COMPLETED
            job.error_message = None
        await self.session.flush()

    # ------------------------------------------------------------------
    # Workflow events
    # ------------------------------------------------------------------

    async def _emit_workflow_started(
        self,
        run_id: UUID,
        job: AutomationJob,
    ) -> None:
        from app.orchestration.events.enums import WorkflowEvent
        from app.orchestration.events.models import DomainEvent
        from app.orchestration.runtime import get_workflow_engine
        from app.orchestration.state.enums import WorkflowState

        engine = get_workflow_engine(self.session)
        status = await engine.get_status(run_id)
        state = WorkflowState(status["state"])
        if state != WorkflowState.PR_CREATED:
            raise BadRequestException(
                "workflow_run_id must be in state 'pull_request_created' "
                f"to emit ExecutionStarted (current={state.value})"
            )
        await engine.on_event(
            DomainEvent(
                event_type=WorkflowEvent.EXECUTION_STARTED,
                correlation_id=run_id,
                organization_id=status.get("organization_id"),
                project_id=status.get("project_id"),
                story_id=status.get("story_id"),
                payload={
                    "automation_job_id": str(job.id),
                    "runner": self.runner.name,
                },
            )
        )

    async def _emit_workflow_completed(
        self,
        run_id: UUID,
        job: AutomationJobResponse,
    ) -> None:
        from app.orchestration.events.enums import WorkflowEvent
        from app.orchestration.events.models import DomainEvent
        from app.orchestration.runtime import get_workflow_engine

        engine = get_workflow_engine(self.session)
        status = await engine.get_status(run_id)
        await engine.on_event(
            DomainEvent(
                event_type=WorkflowEvent.EXECUTION_COMPLETED,
                correlation_id=run_id,
                organization_id=status.get("organization_id"),
                project_id=status.get("project_id"),
                story_id=status.get("story_id"),
                payload={
                    "automation_job_id": str(job.id),
                    "status": job.status.value,
                    "passed": job.passed,
                    "failed": job.failed,
                    "total": job.total,
                    "runner": self.runner.name,
                },
            )
        )

    async def _emit_workflow_failed_to_start(
        self,
        run_id: UUID,
        job: AutomationJob,
        error: str,
    ) -> None:
        from app.orchestration.events.enums import WorkflowEvent
        from app.orchestration.events.models import DomainEvent
        from app.orchestration.runtime import get_workflow_engine
        from app.orchestration.state.enums import WorkflowState

        engine = get_workflow_engine(self.session)
        status = await engine.get_status(run_id)
        state = WorkflowState(status["state"])
        # Only valid from PR_CREATED; if we already moved to STARTED, abort.
        event = (
            WorkflowEvent.EXECUTION_ABORTED
            if state == WorkflowState.EXECUTION_STARTED
            else WorkflowEvent.EXECUTION_FAILED_TO_START
        )
        try:
            await engine.on_event(
                DomainEvent(
                    event_type=event,
                    correlation_id=run_id,
                    organization_id=status.get("organization_id"),
                    project_id=status.get("project_id"),
                    story_id=status.get("story_id"),
                    payload={
                        "automation_job_id": str(job.id),
                        "error": error,
                    },
                )
            )
        except BadRequestException:
            # Best-effort workflow sync; do not mask the original error.
            pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _job_response(self, job: AutomationJob) -> AutomationJobResponse:
        executions = [
            ExecutionResponse.model_validate(ex)
            for ex in (job.executions or [])
            if not ex.is_deleted
        ]
        passed = sum(1 for e in executions if e.status == ExecutionStatus.PASSED)
        failed = sum(1 for e in executions if e.status == ExecutionStatus.FAILED)
        error = sum(1 for e in executions if e.status == ExecutionStatus.ERROR)
        skipped = sum(1 for e in executions if e.status == ExecutionStatus.SKIPPED)
        summary = AutomationJobSummary.model_validate(job)
        return AutomationJobResponse(
            **summary.model_dump(),
            executions=executions,
            passed=passed,
            failed=failed,
            error=error,
            skipped=skipped,
            total=len(executions),
        )

    async def _get_story(self, story_id: UUID) -> Story:
        story = await self.story_repo.get_by_id(story_id)
        if story is None:
            # Fallback query without soft-delete quirks
            stmt = (
                select(Story)
                .options(
                    noload(Story.acceptance_criteria),
                    noload(Story.test_cases),
                    noload(Story.bugs),
                    noload(Story.project),
                    noload(Story.sprint),
                )
                .where(Story.id == story_id, Story.is_deleted.is_(False))
            )
            result = await self.session.execute(stmt)
            story = result.scalar_one_or_none()
        if story is None:
            raise NotFoundException("Story", str(story_id))
        return story

    async def _get_artifact(self, artifact_id: UUID) -> AutomationArtifact:
        artifact = await self.artifact_repo.get_by_id(artifact_id)
        if artifact is None:
            raise NotFoundException("AutomationArtifact", str(artifact_id))
        return artifact

    async def _get_test_case(self, test_case_id: UUID) -> TestCase:
        tc = await self.test_case_repo.get_by_id(test_case_id)
        if tc is None:
            raise NotFoundException("TestCase", str(test_case_id))
        return tc

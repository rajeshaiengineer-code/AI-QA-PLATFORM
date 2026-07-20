"""
WorkflowEngine — sole mutator of WorkflowState.

Persists runs/logs, validates transitions, publishes DomainEvents,
and applies retry policy for retryable stage failures.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.project import Project
from app.models.story import Story
from app.models.workflow_log import WorkflowLog
from app.models.workflow_run import WorkflowRun
from app.orchestration.agents.base import AgentContext
from app.orchestration.agents.registry import AgentRegistry
from app.orchestration.engine.retry import RetryPolicy
from app.orchestration.events.bus import InProcessEventBus
from app.orchestration.events.enums import WorkflowEvent
from app.orchestration.events.models import DomainEvent
from app.orchestration.state.enums import WorkflowState
from app.orchestration.state.transitions import (
    TransitionError,
    next_auto_event,
    transition_for,
)


class WorkflowEngine:
    """Persisted workflow orchestrator."""

    def __init__(
        self,
        session: AsyncSession,
        bus: InProcessEventBus,
        agent_registry: Optional[AgentRegistry] = None,
        retry_policy: Optional[RetryPolicy] = None,
    ) -> None:
        self.session = session
        self.bus = bus
        self.agents = agent_registry or AgentRegistry()
        self.retry_policy = retry_policy or RetryPolicy()

    async def start(
        self,
        *,
        story_id: UUID,
        mark_synced: bool = True,
        max_retries: int = 3,
    ) -> WorkflowRun:
        story = await self._get_story(story_id)
        project = await self._get_project(story.project_id)

        run = WorkflowRun(
            story_id=story.id,
            project_id=story.project_id,
            organization_id=project.organization_id,
            state=WorkflowState.NEW.value,
            max_retries=max_retries,
        )
        self.session.add(run)
        await self.session.flush()

        await self._log(
            run,
            message="Workflow started",
            from_state=None,
            to_state=WorkflowState.NEW.value,
            level="info",
        )

        if mark_synced:
            await self._apply_event(
                run,
                WorkflowEvent.STORY_IMPORTED,
                payload={"source": "start"},
            )

        await self.session.flush()
        return run

    async def on_event(self, event: DomainEvent) -> WorkflowRun:
        run = await self._get_run(event.correlation_id)
        return await self._apply_event(
            run,
            event.event_type,
            payload=event.payload,
            causation_id=event.event_id,
            publish=True,
            incoming=event,
        )

    async def advance(self, run_id: UUID) -> WorkflowRun:
        """
        Drive the next automatic stage.

        If an agent is registered for the upstream event that produced the
        current state, it is invoked. Otherwise applies the happy-path
        auto event (except QA gate).
        """
        run = await self._get_run(run_id)
        state = WorkflowState(run.state)
        if state.is_terminal:
            raise BadRequestException(f"Run is terminal ({state.value})")

        if state == WorkflowState.TEST_CASES_GENERATED:
            raise BadRequestException(
                "QA approval required — call approve() before advancing"
            )

        auto_event = next_auto_event(state)
        if auto_event is None:
            raise BadRequestException(
                f"No automatic advance from state '{state.value}'"
            )

        # Prefer registered agents triggered by the event that landed us here.
        trigger = run.last_event
        agents = []
        if trigger:
            try:
                agents = self.agents.resolve(WorkflowEvent(trigger))
            except ValueError:
                agents = []

        if agents:
            agent = agents[0]
            context = AgentContext(
                run_id=run.id,
                organization_id=run.organization_id,
                project_id=run.project_id,
                story_id=run.story_id,
                workflow_state=state,
                correlation_id=run.id,
                input={},
                session=self.session,
            )
            result = await agent.run(context)
            if not result.success:
                return await self._handle_failure(
                    run,
                    error=result.error or f"Agent '{agent.name}' failed",
                    retryable=result.retryable,
                    failure_event=self._failure_event_for(state),
                )
            emit = result.emit_event or auto_event
            return await self._apply_event(
                run,
                emit,
                payload=result.output,
            )

        return await self._apply_event(
            run,
            auto_event,
            payload={"source": "advance"},
        )

    async def approve(
        self,
        run_id: UUID,
        *,
        approved: bool,
        reason: Optional[str] = None,
    ) -> WorkflowRun:
        run = await self._get_run(run_id)
        if WorkflowState(run.state) != WorkflowState.TEST_CASES_GENERATED:
            raise BadRequestException(
                "Approve is only valid when state is test_cases_generated"
            )
        event = (
            WorkflowEvent.STORY_APPROVED
            if approved
            else WorkflowEvent.QA_REJECTED_TERMINAL
        )
        return await self._apply_event(
            run,
            event,
            payload={"approved": approved, "reason": reason},
        )

    async def retry(
        self,
        run_id: UUID,
        *,
        from_state: WorkflowState,
    ) -> WorkflowRun:
        run = await self._get_run(run_id)
        if from_state.is_terminal:
            raise BadRequestException("Cannot retry from a terminal state")

        run.state = from_state.value
        run.last_error = None
        run.retry_count = 0
        run.cancelled_at = None
        run.cancel_reason = None
        await self._log(
            run,
            message=f"Retry from state {from_state.value}",
            from_state=None,
            to_state=from_state.value,
            level="info",
            event_type=None,
        )
        await self.session.flush()
        return run

    async def cancel(self, run_id: UUID, reason: str) -> WorkflowRun:
        run = await self._get_run(run_id)
        run = await self._apply_event(
            run,
            WorkflowEvent.WORKFLOW_CANCELLED,
            payload={"reason": reason},
        )
        run.cancelled_at = datetime.now(timezone.utc)
        run.cancel_reason = reason
        await self.session.flush()
        return run

    async def get_status(self, run_id: UUID) -> Dict[str, Any]:
        run = await self._get_run(run_id)
        logs = await self._list_logs(run.id)
        return self._status_view(run, logs)

    async def get_status_by_story(self, story_id: UUID) -> Dict[str, Any]:
        stmt = (
            select(WorkflowRun)
            .options(noload(WorkflowRun.logs))
            .where(
                WorkflowRun.story_id == story_id,
                WorkflowRun.is_deleted.is_(False),
            )
            .order_by(WorkflowRun.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        run = result.scalar_one_or_none()
        if run is None:
            raise NotFoundException("WorkflowRun", f"story={story_id}")
        logs = await self._list_logs(run.id)
        return self._status_view(run, logs)

    async def _apply_event(
        self,
        run: WorkflowRun,
        event_type: WorkflowEvent,
        *,
        payload: Optional[Dict[str, Any]] = None,
        causation_id: Optional[UUID] = None,
        publish: bool = True,
        incoming: Optional[DomainEvent] = None,
    ) -> WorkflowRun:
        current = WorkflowState(run.state)
        try:
            next_state = transition_for(current, event_type)
        except TransitionError as exc:
            raise BadRequestException(str(exc)) from exc

        from_state = current.value
        run.state = next_state.value
        run.last_event = event_type.value
        if next_state == WorkflowState.FAILED:
            run.last_error = (payload or {}).get("error") or event_type.value

        await self._log(
            run,
            message=f"Transition {from_state} → {next_state.value} via {event_type.value}",
            from_state=from_state,
            to_state=next_state.value,
            event_type=event_type.value,
            payload=payload,
            level="error" if next_state == WorkflowState.FAILED else "info",
        )

        domain_event = incoming or DomainEvent(
            event_type=event_type,
            correlation_id=run.id,
            causation_id=causation_id,
            organization_id=run.organization_id,
            project_id=run.project_id,
            story_id=run.story_id,
            payload=payload or {},
        )

        if next_state == WorkflowState.COMPLETED:
            completed = DomainEvent(
                event_type=WorkflowEvent.WORKFLOW_COMPLETED,
                correlation_id=run.id,
                organization_id=run.organization_id,
                project_id=run.project_id,
                story_id=run.story_id,
                payload={},
            )
            if publish:
                await self.bus.publish(domain_event)
                await self.bus.publish(completed)
        elif next_state == WorkflowState.FAILED:
            failed = DomainEvent(
                event_type=WorkflowEvent.WORKFLOW_FAILED,
                correlation_id=run.id,
                organization_id=run.organization_id,
                project_id=run.project_id,
                story_id=run.story_id,
                payload=payload or {},
            )
            if publish:
                await self.bus.publish(domain_event)
                await self.bus.publish(failed)
        elif publish:
            await self.bus.publish(domain_event)

        await self.session.flush()
        return run

    async def _handle_failure(
        self,
        run: WorkflowRun,
        *,
        error: str,
        retryable: bool,
        failure_event: WorkflowEvent,
    ) -> WorkflowRun:
        attempt = run.retry_count + 1
        run.retry_count = attempt
        run.last_error = error
        await self._log(
            run,
            message=f"Stage failure (attempt {attempt}): {error}",
            level="warn",
            payload={"retryable": retryable, "attempt": attempt},
        )

        if self.retry_policy.should_retry(attempt, retryable):
            await self._log(
                run,
                message=(
                    f"Retry scheduled (delay="
                    f"{self.retry_policy.delay_seconds(attempt)}s)"
                ),
                level="info",
            )
            await self.session.flush()
            return run

        return await self._apply_event(
            run,
            failure_event,
            payload={"error": error},
        )

    def _failure_event_for(self, state: WorkflowState) -> WorkflowEvent:
        mapping = {
            WorkflowState.NEW: WorkflowEvent.IMPORT_FAILED,
            WorkflowState.SYNCED: WorkflowEvent.ANALYSIS_FAILED,
            WorkflowState.ANALYZED: WorkflowEvent.TEST_GEN_FAILED,
            WorkflowState.QA_APPROVED: WorkflowEvent.BDD_FAILED,
            WorkflowState.BDD_GENERATED: WorkflowEvent.AUTOMATION_FAILED,
            WorkflowState.AUTOMATION_GENERATED: WorkflowEvent.PR_FAILED,
            WorkflowState.PR_CREATED: WorkflowEvent.EXECUTION_FAILED_TO_START,
            WorkflowState.EXECUTION_STARTED: WorkflowEvent.EXECUTION_ABORTED,
            WorkflowState.EXECUTION_COMPLETED: WorkflowEvent.WORKFLOW_FAILED,
            WorkflowState.FAILURE_ANALYZED: WorkflowEvent.WORKFLOW_FAILED,
        }
        return mapping.get(state, WorkflowEvent.WORKFLOW_FAILED)

    async def _get_run(self, run_id: UUID) -> WorkflowRun:
        stmt = (
            select(WorkflowRun)
            .options(noload(WorkflowRun.logs))
            .where(WorkflowRun.id == run_id, WorkflowRun.is_deleted.is_(False))
        )
        result = await self.session.execute(stmt)
        run = result.scalar_one_or_none()
        if run is None:
            raise NotFoundException("WorkflowRun", str(run_id))
        return run

    async def _get_story(self, story_id: UUID) -> Story:
        stmt = (
            select(Story)
            .options(
                noload(Story.acceptance_criteria),
                noload(Story.test_cases),
                noload(Story.bugs),
                noload(Story.project),
                noload(Story.sprint),
            )
            .where(
                Story.id == story_id,
                Story.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        story = result.scalar_one_or_none()
        if story is None:
            raise NotFoundException("Story", str(story_id))
        return story

    async def _get_project(self, project_id: UUID) -> Project:
        stmt = (
            select(Project)
            .options(
                noload(Project.organization),
                noload(Project.sprints),
                noload(Project.stories),
                noload(Project.automation_jobs),
                noload(Project.bugs),
            )
            .where(
                Project.id == project_id,
                Project.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        project = result.scalar_one_or_none()
        if project is None:
            raise NotFoundException("Project", str(project_id))
        return project

    async def _list_logs(self, run_id: UUID) -> List[WorkflowLog]:
        stmt = (
            select(WorkflowLog)
            .where(
                WorkflowLog.run_id == run_id,
                WorkflowLog.is_deleted.is_(False),
            )
            .order_by(WorkflowLog.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _log(
        self,
        run: WorkflowRun,
        *,
        message: str,
        level: str = "info",
        event_type: Optional[str] = None,
        from_state: Optional[str] = None,
        to_state: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = WorkflowLog(
            run_id=run.id,
            level=level,
            event_type=event_type,
            from_state=from_state,
            to_state=to_state,
            message=message,
            payload=payload,
        )
        self.session.add(entry)
        await self.session.flush()

    def _status_view(
        self,
        run: WorkflowRun,
        logs: List[WorkflowLog],
    ) -> Dict[str, Any]:
        return {
            "id": run.id,
            "story_id": run.story_id,
            "project_id": run.project_id,
            "organization_id": run.organization_id,
            "state": run.state,
            "last_event": run.last_event,
            "retry_count": run.retry_count,
            "max_retries": run.max_retries,
            "last_error": run.last_error,
            "cancelled_at": run.cancelled_at,
            "cancel_reason": run.cancel_reason,
            "created_at": run.created_at,
            "updated_at": run.updated_at,
            "version": run.version,
            "logs": [
                {
                    "id": log.id,
                    "level": log.level,
                    "event_type": log.event_type,
                    "from_state": log.from_state,
                    "to_state": log.to_state,
                    "message": log.message,
                    "payload": log.payload,
                    "created_at": log.created_at,
                }
                for log in logs
            ],
        }

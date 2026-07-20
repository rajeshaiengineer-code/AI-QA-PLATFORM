"""
Jira Bug Creation Service

Creates a Jira Bug from a failed execution (+ failure analysis) and
persists a local Bug row with external_id + metadata links.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.connectors.exceptions import (
    ConnectorConnectionError,
    ConnectorCredentialError,
)
from app.connectors.jira.connector import JiraConnector
from app.core.config import settings
from app.core.exceptions import BadRequestException, NotFoundException
from app.models.bug import Bug
from app.models.enums import BugStatus, ExecutionStatus, Priority
from app.models.execution import Execution
from app.models.failure_analysis import FailureAnalysis
from app.models.test_case import TestCase
from app.repositories.bug import BugRepository
from app.repositories.execution import ExecutionRepository
from app.repositories.failure_analysis import FailureAnalysisRepository
from app.schemas.bug import BugResponse, CreateJiraBugRequest, CreateJiraBugResponse
from app.services.jira_connector import JiraConnectorService

_FILABLE_STATUSES = {
    ExecutionStatus.FAILED,
    ExecutionStatus.ERROR,
    ExecutionStatus.BLOCKED,
}

_PRIORITY_TO_JIRA = {
    Priority.CRITICAL: "Highest",
    Priority.HIGH: "High",
    Priority.MEDIUM: "Medium",
    Priority.LOW: "Low",
}


class BugCreationService:
    """Create Jira bugs from failed executions and persist local Bug entities."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        jira_service: Optional[JiraConnectorService] = None,
        connector: Optional[JiraConnector] = None,
    ) -> None:
        self.session = session
        self.execution_repo = ExecutionRepository(session)
        self.analysis_repo = FailureAnalysisRepository(session)
        self.bug_repo = BugRepository(session)
        self._jira_service = jira_service or JiraConnectorService()
        self._connector_override = connector

    async def create_jira_bug(
        self,
        execution_id: UUID,
        request: CreateJiraBugRequest,
    ) -> CreateJiraBugResponse:
        execution = await self.execution_repo.get_by_id(execution_id)
        if execution is None:
            raise NotFoundException("Execution", str(execution_id))

        status = (
            execution.status
            if isinstance(execution.status, ExecutionStatus)
            else ExecutionStatus(str(execution.status))
        )
        if status not in _FILABLE_STATUSES:
            raise BadRequestException(
                message=(
                    f"Execution status '{status.value}' cannot file a bug — "
                    "expected failed, error, or blocked"
                ),
                details={"execution_id": str(execution_id), "status": status.value},
            )

        analysis = await self._resolve_analysis(execution_id, request.failure_analysis_id)
        test_case = await self._get_test_case(execution.test_case_id)
        job = execution.automation_job
        if job is None:
            raise BadRequestException(
                message="Execution is missing its automation job",
                details={"execution_id": str(execution_id)},
            )

        priority = request.priority or Priority.MEDIUM
        title = self._build_title(request, analysis, test_case, execution)
        description = self._build_description(
            request,
            analysis,
            test_case,
            execution,
        )
        logs_url = request.logs_url or (analysis.logs if analysis else None)
        execution_url = request.execution_url or (
            f"{settings.API_V1_PREFIX}/executions/{execution.id}"
        )

        connector = self._get_connector()
        try:
            if not connector.is_connected:
                await connector.connect()
            created = await connector.create_issue(
                project_key=request.jira_project_key.strip(),
                summary=title,
                description=description,
                issue_type=request.issue_type,
                priority_name=_PRIORITY_TO_JIRA.get(priority, "Medium"),
                labels=request.labels,
            )
        except (ConnectorCredentialError, ConnectorConnectionError) as exc:
            raise BadRequestException(
                message=f"Jira bug creation failed: {exc}",
                details=getattr(exc, "details", None) or {},
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise BadRequestException(
                message=f"Jira bug creation failed: {exc}",
            ) from exc

        jira_key = str(created.get("key") or "")
        jira_id = str(created.get("id")) if created.get("id") else None
        if not jira_key:
            raise BadRequestException(
                message="Jira create issue response missing key",
                details={"response": created},
            )

        base_url = str(connector.get_config_value("base_url") or "").rstrip("/")
        jira_url = f"{base_url}/browse/{jira_key}" if base_url else None

        extra_metadata: Dict[str, Any] = {
            "summary": analysis.summary if analysis else title,
            "logs_url": logs_url,
            "execution_url": execution_url,
            "jira_url": jira_url,
            "jira_id": jira_id,
            "suggested_fix": analysis.suggested_fix if analysis else None,
            "root_cause": analysis.root_cause if analysis else None,
            "category": analysis.category if analysis else None,
        }

        now = datetime.now(timezone.utc)
        bug = Bug(
            project_id=job.project_id,
            story_id=test_case.story_id if test_case else None,
            test_case_id=execution.test_case_id,
            execution_id=execution.id,
            failure_analysis_id=analysis.id if analysis else None,
            title=title,
            description=description,
            status=BugStatus.OPEN,
            priority=priority,
            external_id=jira_key,
            extra_metadata=extra_metadata,
            created_at=now,
            updated_at=now,
        )
        created_bug = await self.bug_repo.add(bug)
        return CreateJiraBugResponse(
            bug=BugResponse.model_validate(created_bug),
            jira_key=jira_key,
            jira_id=jira_id,
            jira_url=jira_url,
        )

    def _get_connector(self) -> JiraConnector:
        if self._connector_override is not None:
            return self._connector_override
        return self._jira_service.get_connected_connector()

    async def _resolve_analysis(
        self,
        execution_id: UUID,
        analysis_id: Optional[UUID],
    ) -> Optional[FailureAnalysis]:
        if analysis_id is not None:
            analysis = await self.analysis_repo.get_by_id(analysis_id)
            if analysis is None:
                raise NotFoundException("FailureAnalysis", str(analysis_id))
            if analysis.execution_id != execution_id:
                raise BadRequestException(
                    message="FailureAnalysis does not belong to this execution",
                    details={
                        "execution_id": str(execution_id),
                        "failure_analysis_id": str(analysis_id),
                    },
                )
            return analysis
        return await self.analysis_repo.get_latest_for_execution(execution_id)

    async def _get_test_case(self, test_case_id: UUID) -> Optional[TestCase]:
        stmt = (
            select(TestCase)
            .options(
                noload(TestCase.story),
                noload(TestCase.acceptance_criteria),
                noload(TestCase.executions),
                noload(TestCase.bugs),
                noload(TestCase.versions),
            )
            .where(
                TestCase.id == test_case_id,
                TestCase.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _build_title(
        request: CreateJiraBugRequest,
        analysis: Optional[FailureAnalysis],
        test_case: Optional[TestCase],
        execution: Execution,
    ) -> str:
        if request.title:
            return request.title.strip()
        if analysis and analysis.summary:
            summary = analysis.summary.strip()
            return summary[:500] if len(summary) <= 500 else summary[:497] + "..."
        if test_case:
            return f"[Auto] Test failed: {test_case.title}"[:500]
        return f"[Auto] Execution {execution.id} failed"

    @staticmethod
    def _build_description(
        request: CreateJiraBugRequest,
        analysis: Optional[FailureAnalysis],
        test_case: Optional[TestCase],
        execution: Execution,
    ) -> str:
        if request.description:
            return request.description

        lines = [
            "h2. Automated Bug from AI QA Platform",
            "",
            f"*Execution:* {execution.id}",
            f"*Status:* {getattr(execution.status, 'value', execution.status)}",
        ]
        if test_case:
            lines.append(f"*Test case:* {test_case.title}")
            lines.append(f"*Test case id:* {test_case.id}")
        if execution.error_message:
            lines.extend(["", "h3. Error", "{code}", execution.error_message, "{code}"])
        if execution.stack_trace:
            lines.extend(["", "h3. Stack trace", "{code}", execution.stack_trace, "{code}"])
        if analysis:
            lines.extend(
                [
                    "",
                    "h3. Failure analysis",
                    f"*Category:* {analysis.category}",
                    f"*Root cause:* {analysis.root_cause}",
                    f"*Suggested fix:* {analysis.suggested_fix}",
                    f"*Summary:* {analysis.summary}",
                ]
            )
            if analysis.logs:
                lines.append(f"*Logs:* {analysis.logs}")
            if analysis.screenshot_url:
                lines.append(f"*Screenshot:* {analysis.screenshot_url}")
            if analysis.video_url:
                lines.append(f"*Video:* {analysis.video_url}")
            if analysis.network_url:
                lines.append(f"*Network:* {analysis.network_url}")
            if analysis.trace_url:
                lines.append(f"*Trace:* {analysis.trace_url}")
        if request.logs_url:
            lines.append(f"*Logs link:* {request.logs_url}")
        if request.execution_url:
            lines.append(f"*Execution link:* {request.execution_url}")
        elif execution.id:
            lines.append(
                f"*Execution link:* {settings.API_V1_PREFIX}/executions/{execution.id}"
            )
        return "\n".join(lines)

"""GitHubPRAgent — workflow plugin that opens a PR for automation artifacts."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestration.agents.base import AgentContext, AgentResult
from app.orchestration.events.enums import WorkflowEvent
from app.repositories.automation_artifact import AutomationArtifactRepository
from app.schemas.github import (
    GitHubCommitRequest,
    GitHubCreateBranchRequest,
    GitHubPullRequestRequest,
)
from app.services.github_connector import GitHubConnectorService

ServiceFactory = Callable[[AsyncSession], GitHubConnectorService]


class GitHubPRAgent:
    """
    Agent registered for ``automation_generated``.

    Creates a branch, commits automation artifact files, opens a pull request,
    and emits ``pull_request_created`` on success (or ``pr_failed`` on error).

    Expected ``context.input`` keys (optional when connector defaults exist):
      - owner, repo, base_branch, branch_name
      - automation_artifact_id (else latest artifact for the story)
      - pr_title, pr_body, commit_message, draft
    """

    name: str = "github_pr"
    supported_events: List[WorkflowEvent] = [
        WorkflowEvent.AUTOMATION_GENERATED,
    ]

    def __init__(
        self,
        *,
        service_factory: Optional[ServiceFactory] = None,
    ) -> None:
        self._service_factory = service_factory or (
            lambda session: GitHubConnectorService(session=session)
        )

    async def run(self, context: AgentContext) -> AgentResult:
        if context.session is None:
            return AgentResult(
                success=False,
                error="Agent context is missing a database session",
                emit_event=WorkflowEvent.PR_FAILED,
                retryable=False,
            )

        service = self._service_factory(context.session)
        payload = context.input or {}

        try:
            artifact_id = await self._resolve_artifact_id(
                context.session, context.story_id, payload
            )
            branch_name = (
                payload.get("branch_name")
                or f"qa/automation-{str(context.story_id)[:8]}"
            )
            base_branch = payload.get("base_branch")
            owner = payload.get("owner")
            repo = payload.get("repo")
            commit_message = (
                payload.get("commit_message")
                or f"Add Playwright automation for story {context.story_id}"
            )
            pr_title = (
                payload.get("pr_title")
                or f"QA automation: story {context.story_id}"
            )
            pr_body = payload.get("pr_body") or (
                f"Automated pull request for story `{context.story_id}`.\n\n"
                f"Artifact: `{artifact_id}`"
            )
            draft = bool(payload.get("draft", False))

            await service.create_branch(
                GitHubCreateBranchRequest(
                    branch_name=branch_name,
                    from_branch=base_branch,
                    owner=owner,
                    repo=repo,
                )
            )
            commit = await service.commit(
                GitHubCommitRequest(
                    branch=branch_name,
                    message=commit_message,
                    automation_artifact_id=artifact_id,
                    owner=owner,
                    repo=repo,
                )
            )
            pr = await service.create_pull_request(
                GitHubPullRequestRequest(
                    title=pr_title,
                    head=branch_name,
                    base=base_branch,
                    body=pr_body,
                    draft=draft,
                    owner=owner,
                    repo=repo,
                )
            )
        except Exception as exc:
            return AgentResult(
                success=False,
                error=str(exc),
                emit_event=WorkflowEvent.PR_FAILED,
                retryable=True,
                output={"error": str(exc)},
            )

        return AgentResult(
            success=True,
            emit_event=WorkflowEvent.PULL_REQUEST_CREATED,
            output={
                "story_id": str(context.story_id),
                "automation_artifact_id": str(artifact_id),
                "branch": branch_name,
                "commit_sha": commit.sha,
                "pr_number": pr.number,
                "pr_url": pr.html_url,
                "owner": pr.owner,
                "repo": pr.repo,
            },
            artifacts=[
                {
                    "type": "pull_request",
                    "number": pr.number,
                    "html_url": pr.html_url,
                    "branch": branch_name,
                }
            ],
        )

    async def _resolve_artifact_id(
        self,
        session: AsyncSession,
        story_id: UUID,
        payload: Dict[str, Any],
    ) -> UUID:
        raw = payload.get("automation_artifact_id")
        if raw:
            return UUID(str(raw))

        repo = AutomationArtifactRepository(session)
        rows, _total = await repo.list_for_story(story_id, offset=0, limit=1)
        if not rows:
            raise ValueError(
                f"No automation artifacts found for story {story_id}"
            )
        return rows[0].id

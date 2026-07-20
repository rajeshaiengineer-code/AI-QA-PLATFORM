"""
GitHub connector application service — connect / SCM operations via framework.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.connectors.base.types import (
    ConnectorEnvironment,
    CredentialType,
    HealthStatus,
)
from app.connectors.config.models import ConnectorConfig
from app.connectors.credentials.models import ConnectorCredentials
from app.connectors.exceptions import (
    ConnectorConnectionError,
    ConnectorCredentialError,
    ConnectorDisabledError,
    ConnectorNotFoundError,
)
from app.connectors.github.connector import GitHubConnector
from app.connectors.github.constants import (
    DEFAULT_BASE_BRANCH,
    GITHUB_API_BASE,
    GITHUB_CONNECTOR_NAME,
)
from app.connectors.runtime import (
    config_manager,
    connector_factory,
    credential_manager,
)
from app.core.exceptions import BadRequestException, NotFoundException, ServiceUnavailableException
from app.models.automation_artifact import AutomationArtifact
from app.repositories.automation_artifact import AutomationArtifactRepository
from app.schemas.github import (
    GitHubCheckRunItem,
    GitHubCommitRequest,
    GitHubCommitResponse,
    GitHubConnectRequest,
    GitHubConnectResponse,
    GitHubCreateBranchRequest,
    GitHubCreateBranchResponse,
    GitHubFileContent,
    GitHubHealthResponse,
    GitHubMessageResponse,
    GitHubPullRequestRequest,
    GitHubPullRequestResponse,
    GitHubPushRequest,
    GitHubStatusCheckItem,
    GitHubStatusChecksResponse,
)

_FILE_GROUPS = (
    "page_objects",
    "locators",
    "fixtures",
    "utilities",
    "assertions",
    "hooks",
    "specs",
)


def flatten_automation_files(artifact: AutomationArtifact) -> List[Dict[str, str]]:
    """Extract ``{path, content}`` entries from an AutomationArtifact."""
    files: List[Dict[str, str]] = []
    seen: set = set()
    for group in _FILE_GROUPS:
        entries = getattr(artifact, group, None) or []
        for item in entries:
            if not isinstance(item, dict):
                continue
            path = (item.get("path") or "").strip().lstrip("/")
            content = item.get("content")
            if not path or content is None:
                continue
            if path in seen:
                continue
            seen.add(path)
            files.append({"path": path, "content": str(content)})
    return files


class GitHubConnectorService:
    """Facade over Connector Framework for GitHub operations."""

    def __init__(self, session: Optional[AsyncSession] = None) -> None:
        self.session = session

    def _get_connector(self) -> GitHubConnector:
        try:
            config = config_manager.get(GITHUB_CONNECTOR_NAME)
            connector = connector_factory.create(
                GITHUB_CONNECTOR_NAME,
                config=config,
                load_credentials=True,
            )
        except ConnectorNotFoundError as exc:
            raise ServiceUnavailableException(
                "GitHub connector is not registered",
                service="github",
            ) from exc
        except ConnectorDisabledError as exc:
            raise ServiceUnavailableException(
                "GitHub connector is disabled",
                service="github",
            ) from exc
        except ConnectorCredentialError as exc:
            raise BadRequestException(
                "GitHub is not connected — call POST /connectors/github/connect first",
                details=exc.details,
            ) from exc

        assert isinstance(connector, GitHubConnector)
        return connector

    async def _ensure_connected(self) -> GitHubConnector:
        connector = self._get_connector()
        if not connector.is_connected:
            try:
                await connector.connect()
            except (ConnectorCredentialError, ConnectorConnectionError) as exc:
                raise BadRequestException(
                    f"Failed to connect to GitHub: {exc.message}",
                    details=exc.details,
                ) from exc
        return connector

    async def connect(self, payload: GitHubConnectRequest) -> GitHubConnectResponse:
        settings: Dict[str, Any] = {
            "api_base_url": (payload.api_base_url or GITHUB_API_BASE).rstrip("/"),
            "default_base_branch": payload.default_base_branch or DEFAULT_BASE_BRANCH,
        }
        if payload.owner:
            settings["owner"] = payload.owner.strip()
        if payload.repo:
            settings["repo"] = payload.repo.strip()

        config = ConnectorConfig(
            connector_name=GITHUB_CONNECTOR_NAME,
            environment=ConnectorEnvironment.DEVELOPMENT,
            settings=settings,
            enabled=True,
        )
        config_manager.save(config)

        credentials = ConnectorCredentials(
            connector_name=GITHUB_CONNECTOR_NAME,
            credential_type=CredentialType.PAT,
            api_key=payload.personal_access_token,
        )
        credential_manager.save(credentials)

        connector = connector_factory.create(
            GITHUB_CONNECTOR_NAME,
            config=config,
            credentials=credentials,
        )
        assert isinstance(connector, GitHubConnector)

        try:
            await connector.connect()
            health = await connector.health_check()
        except (ConnectorCredentialError, ConnectorConnectionError) as exc:
            await connector.disconnect()
            raise BadRequestException(
                f"Failed to connect to GitHub: {exc.message}",
                details=exc.details,
            ) from exc

        login = None
        if health.details:
            login = health.details.get("login")
        return GitHubConnectResponse(
            connected=True,
            message="Connected to GitHub successfully",
            login=login,
            owner=settings.get("owner"),
            repo=settings.get("repo"),
        )

    async def disconnect(self) -> GitHubMessageResponse:
        config = config_manager.get(GITHUB_CONNECTOR_NAME)
        try:
            connector = connector_factory.create(
                GITHUB_CONNECTOR_NAME,
                config=config,
                load_credentials=True,
                require_enabled=False,
            )
            assert isinstance(connector, GitHubConnector)
            await connector.disconnect()
        except Exception:
            pass

        credential_manager.delete(GITHUB_CONNECTOR_NAME)
        if config:
            config_manager.delete(GITHUB_CONNECTOR_NAME, config.environment)

        return GitHubMessageResponse(
            success=True,
            message="Disconnected from GitHub",
        )

    async def health(self) -> GitHubHealthResponse:
        try:
            connector = self._get_connector()
        except BadRequestException as exc:
            return GitHubHealthResponse(
                status=HealthStatus.UNHEALTHY.value,
                version="1.0.0",
                latency_ms=None,
                last_checked=datetime.now(timezone.utc),
                message=str(exc.message),
                details={},
            )

        try:
            if not connector.is_connected:
                await connector.connect()
            result = await connector.health_check()
        except Exception as exc:  # noqa: BLE001
            return GitHubHealthResponse(
                status=HealthStatus.UNHEALTHY.value,
                version=connector.metadata().version,
                latency_ms=None,
                last_checked=datetime.now(timezone.utc),
                message=str(exc),
                details={},
            )

        return GitHubHealthResponse(
            status=result.status.value,
            version=result.version,
            latency_ms=result.latency_ms,
            last_checked=result.last_checked,
            message=result.message,
            details=result.details,
        )

    async def create_branch(
        self, payload: GitHubCreateBranchRequest
    ) -> GitHubCreateBranchResponse:
        connector = await self._ensure_connected()
        try:
            result = await connector.create_branch(
                branch_name=payload.branch_name,
                from_branch=payload.from_branch,
                owner=payload.owner,
                repo=payload.repo,
            )
        except (ConnectorCredentialError, ConnectorConnectionError) as exc:
            raise BadRequestException(exc.message, details=exc.details) from exc

        return GitHubCreateBranchResponse(
            owner=result["owner"],
            repo=result["repo"],
            branch=result["branch"],
            from_branch=result["from_branch"],
            ref=result.get("ref"),
            sha=result.get("sha"),
        )

    async def _resolve_files(
        self,
        *,
        files: Optional[List[GitHubFileContent]],
        automation_artifact_id: Optional[UUID],
    ) -> List[Dict[str, str]]:
        if automation_artifact_id is not None:
            if self.session is None:
                raise BadRequestException(
                    "Database session required when using automation_artifact_id"
                )
            repo = AutomationArtifactRepository(self.session)
            artifact = await repo.get_by_id(automation_artifact_id)
            if artifact is None:
                raise NotFoundException(
                    "AutomationArtifact", str(automation_artifact_id)
                )
            flattened = flatten_automation_files(artifact)
            if not flattened:
                raise BadRequestException(
                    "AutomationArtifact has no file contents to commit"
                )
            return flattened

        if not files:
            raise BadRequestException(
                "Provide files or automation_artifact_id"
            )
        return [{"path": f.path, "content": f.content} for f in files]

    async def commit(self, payload: GitHubCommitRequest) -> GitHubCommitResponse:
        connector = await self._ensure_connected()
        file_list = await self._resolve_files(
            files=payload.files,
            automation_artifact_id=payload.automation_artifact_id,
        )
        try:
            result = await connector.commit_and_push(
                branch=payload.branch,
                message=payload.message,
                files=file_list,
                owner=payload.owner,
                repo=payload.repo,
                author_name=payload.author_name,
                author_email=payload.author_email,
            )
        except (ConnectorCredentialError, ConnectorConnectionError) as exc:
            raise BadRequestException(exc.message, details=exc.details) from exc

        commit = result.get("commit") or {}
        html_url = commit.get("html_url")
        return GitHubCommitResponse(
            owner=result["owner"],
            repo=result["repo"],
            branch=result["branch"],
            sha=result["sha"],
            tree_sha=result.get("tree_sha"),
            files_committed=result.get("files_committed", len(file_list)),
            html_url=html_url,
        )

    async def push(self, payload: GitHubPushRequest) -> GitHubCommitResponse:
        """Push is implemented as commit + update-ref (same as commit)."""
        return await self.commit(
            GitHubCommitRequest(
                branch=payload.branch,
                message=payload.message,
                files=payload.files,
                automation_artifact_id=payload.automation_artifact_id,
                owner=payload.owner,
                repo=payload.repo,
                author_name=payload.author_name,
                author_email=payload.author_email,
            )
        )

    async def create_pull_request(
        self, payload: GitHubPullRequestRequest
    ) -> GitHubPullRequestResponse:
        connector = await self._ensure_connected()
        try:
            result = await connector.create_pull_request(
                title=payload.title,
                head=payload.head,
                base=payload.base,
                body=payload.body,
                draft=payload.draft,
                owner=payload.owner,
                repo=payload.repo,
            )
        except (ConnectorCredentialError, ConnectorConnectionError) as exc:
            raise BadRequestException(exc.message, details=exc.details) from exc

        return GitHubPullRequestResponse(
            owner=result["owner"],
            repo=result["repo"],
            number=result.get("number"),
            html_url=result.get("html_url"),
            title=result.get("title"),
            state=result.get("state"),
            head=result["head"],
            base=result["base"],
            draft=result.get("draft"),
        )

    async def status_checks(
        self,
        *,
        ref: str,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> GitHubStatusChecksResponse:
        if not ref:
            raise BadRequestException("ref is required")
        connector = await self._ensure_connected()
        try:
            result = await connector.get_status_checks(
                ref=ref, owner=owner, repo=repo
            )
        except (ConnectorCredentialError, ConnectorConnectionError) as exc:
            raise BadRequestException(exc.message, details=exc.details) from exc

        statuses = [
            GitHubStatusCheckItem(
                context=s.get("context"),
                state=s.get("state"),
                description=s.get("description"),
                target_url=s.get("target_url"),
            )
            for s in (result.get("statuses") or [])
            if isinstance(s, dict)
        ]
        check_runs = [
            GitHubCheckRunItem(
                id=c.get("id"),
                name=c.get("name"),
                status=c.get("status"),
                conclusion=c.get("conclusion"),
                html_url=c.get("html_url"),
            )
            for c in (result.get("check_runs") or [])
            if isinstance(c, dict)
        ]
        return GitHubStatusChecksResponse(
            owner=result["owner"],
            repo=result["repo"],
            ref=result["ref"],
            state=result.get("state"),
            total_count=result.get("total_count"),
            statuses=statuses,
            check_runs=check_runs,
            check_runs_total=result.get("check_runs_total", 0),
        )

    def get_connected_connector(self) -> GitHubConnector:
        return self._get_connector()

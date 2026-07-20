"""
GitHub Connector — implements BaseConnector for GitHub REST API.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.connectors.base.connector import BaseConnector
from app.connectors.base.types import (
    ConfigurationField,
    ConfigurationSchema,
    ConnectorCategory,
    ConnectorHealth,
    ConnectorMetadata,
    CredentialType,
    HealthStatus,
)
from app.connectors.exceptions import (
    ConnectorConnectionError,
    ConnectorCredentialError,
)
from app.connectors.github.client import GitHubClient
from app.connectors.github.constants import (
    DEFAULT_BASE_BRANCH,
    GITHUB_API_BASE,
    GITHUB_CONNECTOR_NAME,
)


class GitHubConnector(BaseConnector):
    """
    GitHub source-control connector.

    Auth: Personal Access Token (PAT) stored as CredentialType.PAT in CredentialManager.
    Config settings:
      - api_base_url (optional): default https://api.github.com
      - owner (optional default): GitHub org or user
      - repo (optional default): repository name
      - default_base_branch (optional): default ``main``
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._client: Optional[GitHubClient] = None

    def metadata(self) -> ConnectorMetadata:
        return ConnectorMetadata(
            name=GITHUB_CONNECTOR_NAME,
            display_name="GitHub",
            version="1.0.0",
            category=ConnectorCategory.SOURCE_CONTROL,
            description="GitHub REST API connector for branches, commits, and pull requests",
            provider="GitHub",
            homepage="https://docs.github.com/en/rest",
            capabilities=[
                "connect",
                "health_check",
                "create_branch",
                "commit",
                "push",
                "create_pull_request",
                "status_checks",
            ],
            supported_credential_types=[CredentialType.PAT],
            config_schema_version="1.0",
        )

    def configuration_schema(self) -> ConfigurationSchema:
        return ConfigurationSchema(
            schema_version="1.0",
            title="GitHub Configuration",
            description="Connection settings for GitHub",
            fields=[
                ConfigurationField(
                    name="api_base_url",
                    field_type="string",
                    required=False,
                    default=GITHUB_API_BASE,
                    description="GitHub API base URL (use for GitHub Enterprise)",
                ),
                ConfigurationField(
                    name="owner",
                    field_type="string",
                    required=False,
                    description="Default repository owner (org or user)",
                ),
                ConfigurationField(
                    name="repo",
                    field_type="string",
                    required=False,
                    description="Default repository name",
                ),
                ConfigurationField(
                    name="default_base_branch",
                    field_type="string",
                    required=False,
                    default=DEFAULT_BASE_BRANCH,
                    description="Default base branch for new branches and PRs",
                ),
            ],
        )

    def _build_client(self) -> GitHubClient:
        if self.credentials is None:
            raise ConnectorCredentialError("GitHub credentials are not configured")
        token = self.credentials.get_secret_value("api_key")
        if not token:
            raise ConnectorCredentialError(
                "GitHub requires a Personal Access Token (api_key)"
            )
        api_base = (
            self.get_config_value("api_base_url") or GITHUB_API_BASE
        )
        return GitHubClient(token=token, api_base_url=str(api_base))

    @property
    def client(self) -> GitHubClient:
        if self._client is None:
            raise ConnectorConnectionError("GitHub connector is not connected")
        return self._client

    def resolve_repo(
        self,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> Tuple[str, str]:
        resolved_owner = owner or self.get_config_value("owner")
        resolved_repo = repo or self.get_config_value("repo")
        if not resolved_owner or not resolved_repo:
            raise ConnectorCredentialError(
                "GitHub owner and repo are required (pass in request or set in config)",
                details={"owner": resolved_owner, "repo": resolved_repo},
            )
        return str(resolved_owner), str(resolved_repo)


    def default_base_branch(self) -> str:
        return str(
            self.get_config_value("default_base_branch") or DEFAULT_BASE_BRANCH
        )

    async def validate_credentials(self) -> bool:
        if self.credentials is None:
            return False
        if self.credentials.credential_type != CredentialType.PAT:
            return False
        if not self.credentials.api_key:
            return False
        return True

    async def connect(self) -> None:
        if not await self.validate_credentials():
            raise ConnectorCredentialError(
                "Invalid GitHub credentials — PAT required"
            )
        self._client = self._build_client()
        await self._client.open()
        await self._client.get_authenticated_user()
        self._connected = True

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None
        self._connected = False

    async def health_check(self) -> ConnectorHealth:
        try:
            if not self._connected or self._client is None:
                self._client = self._build_client()
                await self._client.open()
            user, latency_ms = await self.client.timed_authenticated_user()
            self._connected = True
            login = user.get("login") or user.get("name")
            return ConnectorHealth(
                status=HealthStatus.HEALTHY,
                version=self.metadata().version,
                latency_ms=round(latency_ms, 2),
                message=f"Authenticated as {login}",
                details={
                    "login": user.get("login"),
                    "id": user.get("id"),
                    "api_base_url": self.get_config_value("api_base_url")
                    or GITHUB_API_BASE,
                    "owner": self.get_config_value("owner"),
                    "repo": self.get_config_value("repo"),
                },
            )
        except Exception as exc:  # noqa: BLE001 — mapped to health status
            return ConnectorHealth(
                status=HealthStatus.UNHEALTHY,
                version=self.metadata().version,
                message=str(exc),
            )

    # ----- Domain helpers used by service / API layer -----

    async def create_branch(
        self,
        *,
        branch_name: str,
        from_branch: Optional[str] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> Dict[str, Any]:
        owner_name, repo_name = self.resolve_repo(owner, repo)
        base = from_branch or self.default_base_branch()
        result = await self.client.create_branch(
            owner_name,
            repo_name,
            branch_name=branch_name,
            from_branch=base,
        )
        return {
            "owner": owner_name,
            "repo": repo_name,
            "branch": branch_name,
            "from_branch": base,
            "ref": result.get("ref"),
            "sha": (result.get("object") or {}).get("sha"),
            "raw": result,
        }

    async def commit_and_push(
        self,
        *,
        branch: str,
        message: str,
        files: List[Dict[str, str]],
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        author_name: Optional[str] = None,
        author_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        owner_name, repo_name = self.resolve_repo(owner, repo)
        author = None
        if author_name and author_email:
            author = {"name": author_name, "email": author_email}
        result = await self.client.commit_files(
            owner_name,
            repo_name,
            branch=branch,
            message=message,
            files=files,
            author=author,
        )
        result["owner"] = owner_name
        result["repo"] = repo_name
        return result

    async def create_pull_request(
        self,
        *,
        title: str,
        head: str,
        base: Optional[str] = None,
        body: Optional[str] = None,
        draft: bool = False,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> Dict[str, Any]:
        owner_name, repo_name = self.resolve_repo(owner, repo)
        base_branch = base or self.default_base_branch()
        pr = await self.client.create_pull_request(
            owner_name,
            repo_name,
            title=title,
            head=head,
            base=base_branch,
            body=body,
            draft=draft,
        )
        return {
            "owner": owner_name,
            "repo": repo_name,
            "number": pr.get("number"),
            "html_url": pr.get("html_url"),
            "title": pr.get("title"),
            "state": pr.get("state"),
            "head": head,
            "base": base_branch,
            "draft": pr.get("draft"),
            "raw": pr,
        }

    async def get_status_checks(
        self,
        *,
        ref: str,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
    ) -> Dict[str, Any]:
        owner_name, repo_name = self.resolve_repo(owner, repo)
        combined = await self.client.get_combined_status(
            owner_name, repo_name, ref
        )
        check_runs: Dict[str, Any] = {}
        try:
            check_runs = await self.client.list_check_runs(
                owner_name, repo_name, ref
            )
        except ConnectorConnectionError:
            # Check Runs API may be unavailable; combined status is enough
            check_runs = {"total_count": 0, "check_runs": []}
        return {
            "owner": owner_name,
            "repo": repo_name,
            "ref": ref,
            "state": combined.get("state"),
            "total_count": combined.get("total_count"),
            "statuses": combined.get("statuses") or [],
            "check_runs": check_runs.get("check_runs") or [],
            "check_runs_total": check_runs.get("total_count", 0),
        }

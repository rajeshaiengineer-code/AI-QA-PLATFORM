"""
Unit tests for GitHub connector (framework-compliant, mocked httpx).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.connectors.base.types import (
    ConnectorEnvironment,
    CredentialType,
    HealthStatus,
)
from app.connectors.config.models import ConnectorConfig
from app.connectors.credentials.models import ConnectorCredentials
from app.connectors.github.client import GitHubClient
from app.connectors.github.connector import GitHubConnector
from app.connectors.registry import ConnectorRegistry
from app.connectors.runtime import register_builtin_connectors
from app.models.automation_artifact import AutomationArtifact
from app.orchestration.agents.base import AgentContext
from app.orchestration.agents.github_pr import GitHubPRAgent
from app.orchestration.events.enums import WorkflowEvent
from app.orchestration.state.enums import WorkflowState
from app.schemas.github import (
    GitHubCommitResponse,
    GitHubCreateBranchResponse,
    GitHubPullRequestResponse,
)
from app.services.github_connector import flatten_automation_files


def _credentials() -> ConnectorCredentials:
    return ConnectorCredentials(
        connector_name="github",
        credential_type=CredentialType.PAT,
        api_key="ghp_test_token_12345678",
    )


def _config(**settings) -> ConnectorConfig:
    defaults = {
        "owner": "acme",
        "repo": "qa-automation",
        "default_base_branch": "main",
    }
    defaults.update(settings)
    return ConnectorConfig(
        connector_name="github",
        environment=ConnectorEnvironment.DEVELOPMENT,
        settings=defaults,
    )


class TestGitHubConnectorFramework:
    def test_registers_with_framework(self):
        registry = ConnectorRegistry()
        registry.register(GitHubConnector)
        assert registry.is_registered("github")
        meta = registry.get("github").resolve_metadata()
        assert meta.name == "github"
        assert CredentialType.PAT in meta.supported_credential_types

    def test_builtin_registration_idempotent(self):
        from app.connectors.runtime import connector_registry

        register_builtin_connectors()
        register_builtin_connectors()
        assert connector_registry.is_registered("github")
        assert connector_registry.is_registered("jira")

    @pytest.mark.asyncio
    async def test_validate_credentials(self):
        connector = GitHubConnector(config=_config(), credentials=_credentials())
        assert await connector.validate_credentials() is True

    @pytest.mark.asyncio
    async def test_health_check_uses_client(self):
        connector = GitHubConnector(config=_config(), credentials=_credentials())
        mock_client = MagicMock()
        mock_client.timed_authenticated_user = AsyncMock(
            return_value=({"login": "octocat", "id": 1}, 8.5)
        )
        mock_client.open = AsyncMock()
        connector._client = mock_client
        connector._connected = True

        health = await connector.health_check()
        assert health.status == HealthStatus.HEALTHY
        assert health.latency_ms == 8.5
        assert "octocat" in (health.message or "")

    @pytest.mark.asyncio
    async def test_create_branch_delegates(self):
        connector = GitHubConnector(config=_config(), credentials=_credentials())
        mock_client = MagicMock()
        mock_client.create_branch = AsyncMock(
            return_value={
                "ref": "refs/heads/feature/x",
                "object": {"sha": "abc123"},
            }
        )
        connector._client = mock_client
        connector._connected = True

        result = await connector.create_branch(
            branch_name="feature/x", from_branch="main"
        )
        assert result["branch"] == "feature/x"
        assert result["sha"] == "abc123"
        mock_client.create_branch.assert_awaited_once()


class TestGitHubClientRetry:
    @pytest.mark.asyncio
    async def test_retries_on_429(self):
        client = GitHubClient("token", max_retries=3)

        ok = MagicMock()
        ok.status_code = 200
        ok.content = b'{"login": "octocat"}'
        ok.json.return_value = {"login": "octocat"}

        limited = MagicMock()
        limited.status_code = 429
        limited.headers = {"Retry-After": "0"}
        limited.text = "rate limited"

        mock_http = MagicMock()
        mock_http.request = AsyncMock(side_effect=[limited, ok])
        mock_http.aclose = AsyncMock()
        client._client = mock_http

        with patch(
            "app.connectors.github.client.asyncio.sleep", new_callable=AsyncMock
        ):
            data = await client.request("GET", "/user")

        assert data == {"login": "octocat"}
        assert mock_http.request.await_count == 2

    @pytest.mark.asyncio
    async def test_commit_files_flow(self):
        client = GitHubClient("token")

        responses = {
            ("GET", "/repos/acme/qa/git/ref/heads/main"): {
                "object": {"sha": "parentsha"}
            },
            ("GET", "/repos/acme/qa/git/commits/parentsha"): {
                "tree": {"sha": "basetree"}
            },
            ("POST", "/repos/acme/qa/git/blobs"): {"sha": "blobsha"},
            ("POST", "/repos/acme/qa/git/trees"): {"sha": "newtree"},
            ("POST", "/repos/acme/qa/git/commits"): {
                "sha": "commitsha",
                "html_url": "https://github.com/acme/qa/commit/commitsha",
            },
            ("PATCH", "/repos/acme/qa/git/refs/heads/main"): {
                "ref": "refs/heads/main",
                "object": {"sha": "commitsha"},
            },
        }

        async def fake_request(method, path, *, params=None, json=None):
            key = (method, path)
            if key not in responses:
                raise AssertionError(f"Unexpected request {key}")
            return responses[key]

        client.request = fake_request  # type: ignore[method-assign]

        result = await client.commit_files(
            "acme",
            "qa",
            branch="main",
            message="Add specs",
            files=[{"path": "tests/a.spec.ts", "content": "test('x', () => {});"}],
        )
        assert result["sha"] == "commitsha"
        assert result["files_committed"] == 1


class TestFlattenAutomationFiles:
    def test_flattens_groups(self):
        artifact = AutomationArtifact(
            story_id=uuid4(),
            name="suite",
            page_objects=[
                {"path": "pages/A.ts", "content": "export class A {}"},
            ],
            specs=[
                {"path": "tests/a.spec.ts", "content": "test('a', () => {});"},
            ],
            locators=[],
        )
        files = flatten_automation_files(artifact)
        paths = {f["path"] for f in files}
        assert "pages/A.ts" in paths
        assert "tests/a.spec.ts" in paths


class TestGitHubPRAgent:
    @pytest.mark.asyncio
    async def test_emits_pull_request_created(self):
        artifact_id = uuid4()
        story_id = uuid4()

        mock_service = MagicMock()
        mock_service.create_branch = AsyncMock(
            return_value=GitHubCreateBranchResponse(
                owner="acme",
                repo="qa",
                branch="qa/automation-abc",
                from_branch="main",
                sha="branchsha",
            )
        )
        mock_service.commit = AsyncMock(
            return_value=GitHubCommitResponse(
                owner="acme",
                repo="qa",
                branch="qa/automation-abc",
                sha="commitsha",
                files_committed=2,
            )
        )
        mock_service.create_pull_request = AsyncMock(
            return_value=GitHubPullRequestResponse(
                owner="acme",
                repo="qa",
                number=42,
                html_url="https://github.com/acme/qa/pull/42",
                title="QA automation",
                state="open",
                head="qa/automation-abc",
                base="main",
            )
        )

        agent = GitHubPRAgent(service_factory=lambda _s: mock_service)
        context = AgentContext(
            run_id=uuid4(),
            story_id=story_id,
            workflow_state=WorkflowState.AUTOMATION_GENERATED,
            correlation_id=uuid4(),
            session=MagicMock(),
            input={
                "automation_artifact_id": str(artifact_id),
                "owner": "acme",
                "repo": "qa",
                "branch_name": "qa/automation-abc",
            },
        )

        result = await agent.run(context)
        assert result.success is True
        assert result.emit_event == WorkflowEvent.PULL_REQUEST_CREATED
        assert result.output["pr_number"] == 42
        mock_service.create_branch.assert_awaited_once()
        mock_service.commit.assert_awaited_once()
        mock_service.create_pull_request.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_emits_pr_failed_without_session(self):
        agent = GitHubPRAgent()
        context = AgentContext(
            run_id=uuid4(),
            story_id=uuid4(),
            workflow_state=WorkflowState.AUTOMATION_GENERATED,
            correlation_id=uuid4(),
            session=None,
        )
        result = await agent.run(context)
        assert result.success is False
        assert result.emit_event == WorkflowEvent.PR_FAILED

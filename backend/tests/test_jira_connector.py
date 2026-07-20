"""
Unit tests for Jira Cloud connector (framework-compliant).
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.connectors.base.types import (
    ConnectorEnvironment,
    CredentialType,
    HealthStatus,
)
from app.connectors.config.models import ConnectorConfig
from app.connectors.credentials.models import ConnectorCredentials
from app.connectors.jira.client import JiraClient
from app.connectors.jira.connector import JiraConnector
from app.connectors.jira.mapper import (
    map_issue,
    map_priority,
    map_status,
    map_story_type,
    parse_acceptance_criteria,
)
from app.connectors.registry import ConnectorRegistry
from app.connectors.runtime import register_builtin_connectors
from app.models.enums import Priority, StoryStatus, StoryType


class TestJiraMapper:
    def test_map_priority(self):
        assert map_priority({"name": "Highest"}) == Priority.CRITICAL
        assert map_priority({"name": "High"}) == Priority.HIGH
        assert map_priority({"name": "Medium"}) == Priority.MEDIUM
        assert map_priority({"name": "Low"}) == Priority.LOW

    def test_map_status(self):
        assert (
            map_status({"name": "Done", "statusCategory": {"key": "done"}})
            == StoryStatus.DONE
        )
        assert (
            map_status({"name": "In Progress", "statusCategory": {"key": "indeterminate"}})
            == StoryStatus.IN_PROGRESS
        )
        assert map_status({"name": "Blocked"}) == StoryStatus.BLOCKED

    def test_map_story_type(self):
        assert map_story_type({"name": "Bug"}) == StoryType.BUG
        assert map_story_type({"name": "Story"}) == StoryType.FEATURE
        assert map_story_type({"name": "Spike"}) == StoryType.SPIKE

    def test_parse_acceptance_criteria_from_description(self):
        text = """As a user I want login.

Acceptance Criteria:
- User can enter email
- User receives reset link
"""
        ac = parse_acceptance_criteria(text)
        assert "User can enter email" in ac
        assert "User receives reset link" in ac

    def test_map_issue_preserves_jira_ids(self):
        issue = {
            "id": "10001",
            "key": "PAY-101",
            "fields": {
                "summary": "Reset password",
                "description": None,
                "status": {"name": "To Do", "statusCategory": {"key": "new"}},
                "issuetype": {"name": "Story"},
                "priority": {"name": "High"},
                "labels": ["auth", "p0"],
                "assignee": {"displayName": "Ada Lovelace"},
                "reporter": {"displayName": "Grace Hopper"},
                "created": "2026-01-01T10:00:00.000+0000",
                "updated": "2026-01-02T11:00:00.000+0000",
            },
        }
        mapped = map_issue(issue)
        assert mapped["jira_issue_id"] == "10001"
        assert mapped["external_id"] == "PAY-101"
        assert mapped["assignee"] == "Ada Lovelace"
        assert mapped["reporter"] == "Grace Hopper"
        assert mapped["labels"] == ["auth", "p0"]
        assert mapped["priority"] == Priority.HIGH
        assert isinstance(mapped["external_updated_at"], datetime)


class TestJiraConnectorFramework:
    def test_registers_with_framework(self):
        registry = ConnectorRegistry()
        registry.register(JiraConnector)
        assert registry.is_registered("jira")
        meta = registry.get("jira").resolve_metadata()
        assert meta.name == "jira"
        assert CredentialType.USERNAME_PASSWORD in meta.supported_credential_types

    def test_builtin_registration_idempotent(self):
        from app.connectors.runtime import connector_registry

        register_builtin_connectors()
        register_builtin_connectors()
        assert connector_registry.is_registered("jira")

    @pytest.mark.asyncio
    async def test_validate_credentials(self):
        connector = JiraConnector(
            config=ConnectorConfig(
                connector_name="jira",
                environment=ConnectorEnvironment.DEVELOPMENT,
                settings={"base_url": "https://example.atlassian.net"},
            ),
            credentials=ConnectorCredentials(
                connector_name="jira",
                credential_type=CredentialType.USERNAME_PASSWORD,
                username="user@example.com",
                password="token-value-123",
            ),
        )
        assert await connector.validate_credentials() is True

    @pytest.mark.asyncio
    async def test_health_check_uses_client(self):
        connector = JiraConnector(
            config=ConnectorConfig(
                connector_name="jira",
                settings={"base_url": "https://example.atlassian.net"},
            ),
            credentials=ConnectorCredentials(
                connector_name="jira",
                credential_type=CredentialType.USERNAME_PASSWORD,
                username="user@example.com",
                password="token-value-123",
            ),
        )
        mock_client = MagicMock()
        mock_client.timed_myself = AsyncMock(
            return_value=({"displayName": "Tester", "accountId": "abc"}, 12.5)
        )
        mock_client.get_server_info = AsyncMock(return_value={"version": "1000.0.0"})
        mock_client.open = AsyncMock()
        connector._client = mock_client
        connector._connected = True

        health = await connector.health_check()
        assert health.status == HealthStatus.HEALTHY
        assert health.latency_ms == 12.5
        assert health.version == "1000.0.0"


class TestJiraClientRetry:
    @pytest.mark.asyncio
    async def test_retries_on_429(self):
        client = JiraClient(
            "https://example.atlassian.net",
            "a@b.com",
            "token",
            max_retries=3,
        )

        ok = MagicMock()
        ok.status_code = 200
        ok.content = b'{"ok": true}'
        ok.json.return_value = {"ok": True}

        limited = MagicMock()
        limited.status_code = 429
        limited.headers = {"Retry-After": "0"}
        limited.text = "rate limited"

        mock_http = MagicMock()
        mock_http.request = AsyncMock(side_effect=[limited, ok])
        mock_http.aclose = AsyncMock()
        client._client = mock_http

        with patch("app.connectors.jira.client.asyncio.sleep", new_callable=AsyncMock):
            data = await client.request("GET", "/rest/api/3/myself")

        assert data == {"ok": True}
        assert mock_http.request.await_count == 2

"""
API / unit tests for Notifications (email stub, Slack/Teams httpx, history, EventBus).
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models.enums import NotificationChannel, NotificationStatus
from app.orchestration.events.enums import WorkflowEvent
from app.orchestration.events.models import DomainEvent
from app.orchestration.runtime import get_event_bus
from app.orchestration.subscribers.notifications import (
    handle_workflow_lifecycle,
    register_notification_subscribers,
    reset_notification_subscribers_for_tests,
)
from app.services.notifications import NotificationService
from app.services.notifications.channels.email import EmailChannel
from app.services.notifications.channels.slack import SlackChannel
from app.services.notifications.channels.teams import TeamsChannel


NOTIFICATIONS_URL = "/api/v1/notifications"


@pytest.fixture
def notification_settings() -> Settings:
    return Settings(
        NOTIFICATIONS_PERSIST=True,
        NOTIFICATIONS_WORKFLOW_HOOK=True,
        NOTIFICATIONS_DEFAULT_RECIPIENT="qa@example.com",
        NOTIFICATIONS_DEFAULT_CHANNEL="email",
        SMTP_FROM="noreply@test.local",
        SMTP_HOST=None,
        SLACK_WEBHOOK_URL="https://hooks.slack.test/services/T00/B00/XXX",
        TEAMS_WEBHOOK_URL="https://outlook.office.test/webhook/xxx",
        AUTH_ENABLED=False,
    )


@pytest.mark.asyncio
async def test_email_channel_logs_without_smtp(
    notification_settings: Settings,
    caplog: pytest.LogCaptureFixture,
) -> None:
    channel = EmailChannel(notification_settings)
    with caplog.at_level("INFO"):
        result = await channel.send(
            recipient="user@example.com",
            subject="Hello",
            body="Body text",
        )
    assert result.success is True
    assert "SMTP stub" in result.message
    assert any("Email notification" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_slack_channel_posts_via_httpx(
    notification_settings: Settings,
) -> None:
    mock_response = Response(200, text="ok")
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_response)

    channel = SlackChannel(notification_settings, client=mock_client)
    result = await channel.send(
        recipient="#qa-alerts",
        subject="Build failed",
        body="Suite X failed",
    )
    assert result.success is True
    mock_client.post.assert_awaited_once()
    args, kwargs = mock_client.post.await_args
    assert args[0] == notification_settings.SLACK_WEBHOOK_URL
    assert "Build failed" in kwargs["json"]["text"]


@pytest.mark.asyncio
async def test_teams_channel_posts_via_httpx(
    notification_settings: Settings,
) -> None:
    mock_response = Response(200, text="1")
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_response)

    channel = TeamsChannel(notification_settings, client=mock_client)
    result = await channel.send(
        recipient="QA Channel",
        subject="Workflow done",
        body="All green",
    )
    assert result.success is True
    mock_client.post.assert_awaited_once()
    args, kwargs = mock_client.post.await_args
    assert args[0] == notification_settings.TEAMS_WEBHOOK_URL
    assert kwargs["json"]["title"] == "Workflow done"


@pytest.mark.asyncio
async def test_slack_missing_webhook_fails(
    notification_settings: Settings,
) -> None:
    notification_settings.SLACK_WEBHOOK_URL = None
    channel = SlackChannel(notification_settings)
    result = await channel.send(
        recipient="#qa",
        subject="x",
        body="y",
    )
    assert result.success is False
    assert result.error_message is not None


@pytest.mark.asyncio
async def test_send_email_api_persists_and_lists(
    client: AsyncClient,
    db_session: AsyncSession,
    notification_settings: Settings,
) -> None:
    with patch(
        "app.services.notifications.service.app_settings",
        notification_settings,
    ), patch(
        "app.api.v1.endpoints.notifications.NotificationService",
        lambda db: NotificationService(db, settings=notification_settings),
    ):
        send_resp = await client.post(
            f"{NOTIFICATIONS_URL}/send",
            json={
                "channel": "email",
                "recipient": "qa@example.com",
                "subject": "Test subject",
                "body": "Test body",
            },
        )
    assert send_resp.status_code == 200, send_resp.text
    payload = send_resp.json()
    assert payload["success"] is True
    assert payload["status"] == "sent"
    assert payload["notification_id"] is not None

    list_resp = await client.get(NOTIFICATIONS_URL)
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] >= 1
    assert data["items"][0]["channel"] == "email"
    assert data["items"][0]["recipient"] == "qa@example.com"


@pytest.mark.asyncio
async def test_send_email_requires_subject(client: AsyncClient) -> None:
    resp = await client.post(
        f"{NOTIFICATIONS_URL}/send",
        json={
            "channel": "email",
            "recipient": "qa@example.com",
            "body": "No subject",
        },
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_send_slack_api_mocks_httpx(
    client: AsyncClient,
    notification_settings: Settings,
) -> None:
    mock_response = Response(200, text="ok")
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_response)

    def _factory(db):
        return NotificationService(
            db,
            settings=notification_settings,
            http_client=mock_client,
        )

    with patch(
        "app.api.v1.endpoints.notifications.NotificationService",
        _factory,
    ):
        resp = await client.post(
            f"{NOTIFICATIONS_URL}/send",
            json={
                "channel": "slack",
                "recipient": "#alerts",
                "subject": "Ping",
                "body": "Hello Slack",
            },
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["success"] is True
    mock_client.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_teams_api_mocks_httpx(
    client: AsyncClient,
    notification_settings: Settings,
) -> None:
    mock_response = Response(200, text="1")
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_response)

    def _factory(db):
        return NotificationService(
            db,
            settings=notification_settings,
            http_client=mock_client,
        )

    with patch(
        "app.api.v1.endpoints.notifications.NotificationService",
        _factory,
    ):
        resp = await client.post(
            f"{NOTIFICATIONS_URL}/send",
            json={
                "channel": "teams",
                "recipient": "Ops",
                "subject": "Ping",
                "body": "Hello Teams",
            },
        )
    assert resp.status_code == 200, resp.text
    assert resp.json()["success"] is True
    mock_client.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_persist_false_skips_history_row(
    client: AsyncClient,
    notification_settings: Settings,
) -> None:
    notification_settings.NOTIFICATIONS_PERSIST = True

    def _factory(db):
        return NotificationService(db, settings=notification_settings)

    with patch(
        "app.api.v1.endpoints.notifications.NotificationService",
        _factory,
    ):
        send_resp = await client.post(
            f"{NOTIFICATIONS_URL}/send",
            json={
                "channel": "email",
                "recipient": "ephemeral@example.com",
                "subject": "No persist",
                "body": "Skip log",
                "persist": False,
            },
        )
    assert send_resp.status_code == 200
    assert send_resp.json()["notification_id"] is None

    list_resp = await client.get(
        NOTIFICATIONS_URL,
        params={"channel": "email"},
    )
    assert list_resp.status_code == 200
    recipients = [i["recipient"] for i in list_resp.json()["items"]]
    assert "ephemeral@example.com" not in recipients


@pytest.mark.asyncio
async def test_auth_enabled_false_send_is_open(client: AsyncClient) -> None:
    """AUTH_ENABLED=false must not require a Bearer token on send."""
    from app.core.config import settings

    assert settings.AUTH_ENABLED is False
    resp = await client.post(
        f"{NOTIFICATIONS_URL}/send",
        json={
            "channel": "email",
            "recipient": "open@example.com",
            "subject": "Open",
            "body": "No auth",
        },
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_workflow_eventbus_hook_sends_email(
    db_session: AsyncSession,
    notification_settings: Settings,
) -> None:
    @asynccontextmanager
    async def _factory() -> AsyncIterator[AsyncSession]:
        yield db_session

    event = DomainEvent(
        event_type=WorkflowEvent.WORKFLOW_COMPLETED,
        correlation_id=uuid4(),
        story_id=uuid4(),
        payload={"workflow_run_id": str(uuid4())},
    )
    await handle_workflow_lifecycle(
        event,
        settings=notification_settings,
        session_factory=_factory,
    )

    service = NotificationService(db_session, settings=notification_settings)
    history = await service.list_history(page=1, page_size=10)
    assert history.total >= 1
    assert any("COMPLETED" in (i.subject or "") for i in history.items)


@pytest.mark.asyncio
async def test_register_subscribers_idempotent(
    notification_settings: Settings,
) -> None:
    bus = get_event_bus()
    bus.clear()
    reset_notification_subscribers_for_tests()
    register_notification_subscribers(notification_settings)
    register_notification_subscribers(notification_settings)
    handlers = bus._handlers[WorkflowEvent.WORKFLOW_COMPLETED]
    assert len(handlers) == 1
    bus.clear()
    reset_notification_subscribers_for_tests()

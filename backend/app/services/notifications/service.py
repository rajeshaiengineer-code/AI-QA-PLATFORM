"""
Notification Service

Orchestrates channel delivery and optional NotificationLog persistence.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, settings as app_settings
from app.core.exceptions import BadRequestException
from app.models.enums import NotificationChannel, NotificationStatus
from app.models.notification_log import NotificationLog
from app.repositories.notification import NotificationLogRepository
from app.schemas.base import PaginatedResponse
from app.schemas.notification import (
    NotificationLogResponse,
    NotificationSendRequest,
    NotificationSendResponse,
)
from app.services.notifications.channels import (
    EmailChannel,
    NotificationChannelPort,
    SlackChannel,
    TeamsChannel,
)


class NotificationService:
    """Application service for outbound notifications."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Optional[Settings] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.session = session
        self.settings = settings or app_settings
        self.repository = NotificationLogRepository(session)
        self._http_client = http_client
        self._channels: Dict[NotificationChannel, NotificationChannelPort] = {
            NotificationChannel.EMAIL: EmailChannel(self.settings),
            NotificationChannel.SLACK: SlackChannel(
                self.settings,
                client=http_client,
            ),
            NotificationChannel.TEAMS: TeamsChannel(
                self.settings,
                client=http_client,
            ),
        }

    def _resolve_channel(
        self,
        channel: NotificationChannel,
    ) -> NotificationChannelPort:
        port = self._channels.get(channel)
        if port is None:
            raise BadRequestException(f"Unsupported notification channel: {channel}")
        return port

    async def send(
        self,
        request: NotificationSendRequest,
        *,
        workflow_run_id: Optional[UUID] = None,
        story_id: Optional[UUID] = None,
        organization_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
    ) -> NotificationSendResponse:
        """
        Deliver a notification on the requested channel.

        Email uses an SMTP stub (log only). Slack/Teams POST to configured webhooks.
        """
        if request.channel == NotificationChannel.EMAIL and not (
            request.subject and request.subject.strip()
        ):
            raise BadRequestException("subject is required for email notifications")

        channel = self._resolve_channel(request.channel)
        result = await channel.send(
            recipient=request.recipient,
            subject=request.subject,
            body=request.body,
        )

        status = (
            NotificationStatus.SENT if result.success else NotificationStatus.FAILED
        )
        notification_id: Optional[UUID] = None
        should_persist = (
            self.settings.NOTIFICATIONS_PERSIST
            if request.persist is None
            else request.persist
        )

        if should_persist:
            log = NotificationLog(
                channel=request.channel.value,
                recipient=request.recipient,
                subject=request.subject,
                body=request.body,
                status=status.value,
                error_message=result.error_message,
                workflow_run_id=workflow_run_id,
                story_id=story_id,
                organization_id=organization_id,
                project_id=project_id,
                extra_data=request.metadata,
            )
            await self.repository.add(log)
            await self.session.commit()
            notification_id = log.id

        return NotificationSendResponse(
            success=result.success,
            channel=request.channel,
            recipient=request.recipient,
            status=status,
            message=result.message,
            notification_id=notification_id,
            error_message=result.error_message,
        )

    async def send_raw(
        self,
        *,
        channel: NotificationChannel,
        recipient: str,
        subject: Optional[str],
        body: str,
        metadata: Optional[Dict[str, Any]] = None,
        workflow_run_id: Optional[UUID] = None,
        story_id: Optional[UUID] = None,
        organization_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        persist: Optional[bool] = None,
    ) -> NotificationSendResponse:
        """Convenience wrapper used by EventBus subscribers."""
        return await self.send(
            NotificationSendRequest(
                channel=channel,
                recipient=recipient,
                subject=subject,
                body=body,
                persist=persist,
                metadata=metadata,
            ),
            workflow_run_id=workflow_run_id,
            story_id=story_id,
            organization_id=organization_id,
            project_id=project_id,
        )

    async def list_history(
        self,
        *,
        channel: Optional[NotificationChannel] = None,
        status: Optional[NotificationStatus] = None,
        organization_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        story_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[NotificationLogResponse]:
        """Return paginated notification history."""
        items, total = await self.repository.list_history(
            channel=channel.value if channel else None,
            status=status.value if status else None,
            organization_id=organization_id,
            project_id=project_id,
            story_id=story_id,
            page=page,
            page_size=page_size,
        )
        responses = [
            NotificationLogResponse.model_validate(row) for row in items
        ]
        return PaginatedResponse.create(
            items=responses,
            total=total,
            page=page,
            page_size=page_size,
        )

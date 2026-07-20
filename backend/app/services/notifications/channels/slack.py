"""Slack incoming-webhook notification channel (httpx)."""

from __future__ import annotations

from typing import Optional

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.services.notifications.channels.base import (
    ChannelSendResult,
    NotificationChannelPort,
)

logger = get_logger(__name__)


class SlackChannel(NotificationChannelPort):
    """Post a text message to a Slack incoming webhook."""

    name = "slack"

    def __init__(self, settings: Settings, client: Optional[httpx.AsyncClient] = None) -> None:
        self.settings = settings
        self._client = client

    async def send(
        self,
        *,
        recipient: str,
        subject: Optional[str],
        body: str,
    ) -> ChannelSendResult:
        webhook = self.settings.SLACK_WEBHOOK_URL
        if not webhook:
            return ChannelSendResult(
                success=False,
                message="Slack webhook not configured",
                error_message="SLACK_WEBHOOK_URL is not set",
            )

        text_parts = []
        if subject:
            text_parts.append(f"*{subject}*")
        text_parts.append(body)
        if recipient:
            text_parts.append(f"_to: {recipient}_")
        payload = {"text": "\n".join(text_parts)}

        try:
            if self._client is not None:
                response = await self._client.post(webhook, json=payload)
            else:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.post(webhook, json=payload)
        except httpx.HTTPError as exc:
            logger.warning(
                "Slack webhook failed",
                extra_fields={"error": str(exc), "recipient": recipient},
            )
            return ChannelSendResult(
                success=False,
                message="Slack webhook request failed",
                error_message=str(exc),
            )

        if response.status_code >= 400:
            err = f"HTTP {response.status_code}"
            logger.warning(
                "Slack webhook failed",
                extra_fields={"error": err, "recipient": recipient},
            )
            return ChannelSendResult(
                success=False,
                message="Slack webhook request failed",
                error_message=err,
            )

        return ChannelSendResult(
            success=True,
            message=f"Slack message delivered (recipient={recipient})",
        )

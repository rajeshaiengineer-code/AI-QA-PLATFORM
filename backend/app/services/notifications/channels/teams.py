"""Microsoft Teams incoming-webhook notification channel (httpx)."""

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


class TeamsChannel(NotificationChannelPort):
    """Post a MessageCard-style payload to a Teams incoming webhook."""

    name = "teams"

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
        webhook = self.settings.TEAMS_WEBHOOK_URL
        if not webhook:
            return ChannelSendResult(
                success=False,
                message="Teams webhook not configured",
                error_message="TEAMS_WEBHOOK_URL is not set",
            )

        title = subject or "AI QA Platform Notification"
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "summary": title,
            "themeColor": "0078D4",
            "title": title,
            "text": body,
            "sections": [
                {
                    "facts": [
                        {"name": "Recipient", "value": recipient},
                    ],
                }
            ],
        }

        try:
            if self._client is not None:
                response = await self._client.post(webhook, json=payload)
            else:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.post(webhook, json=payload)
        except httpx.HTTPError as exc:
            logger.warning(
                "Teams webhook failed",
                extra_fields={"error": str(exc), "recipient": recipient},
            )
            return ChannelSendResult(
                success=False,
                message="Teams webhook request failed",
                error_message=str(exc),
            )

        if response.status_code >= 400:
            err = f"HTTP {response.status_code}"
            logger.warning(
                "Teams webhook failed",
                extra_fields={"error": err, "recipient": recipient},
            )
            return ChannelSendResult(
                success=False,
                message="Teams webhook request failed",
                error_message=err,
            )

        return ChannelSendResult(
            success=True,
            message=f"Teams message delivered (recipient={recipient})",
        )

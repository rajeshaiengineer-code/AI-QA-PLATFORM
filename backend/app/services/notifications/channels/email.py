"""Email notification channel — SMTP stub that logs (no real SMTP)."""

from __future__ import annotations

from typing import Optional

from app.core.config import Settings
from app.core.logging import get_logger
from app.services.notifications.channels.base import (
    ChannelSendResult,
    NotificationChannelPort,
)

logger = get_logger(__name__)


class EmailChannel(NotificationChannelPort):
    """
    MVP email channel.

    Never opens a real SMTP connection. Messages are written to the application
    log so tests and local runs stay offline-safe.
    """

    name = "email"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send(
        self,
        *,
        recipient: str,
        subject: Optional[str],
        body: str,
    ) -> ChannelSendResult:
        from_addr = self.settings.SMTP_FROM
        host = self.settings.SMTP_HOST or "(stub-no-host)"
        logger.info(
            "Email notification (SMTP stub — not sent)",
            extra_fields={
                "channel": self.name,
                "smtp_host": host,
                "smtp_port": self.settings.SMTP_PORT,
                "smtp_from": from_addr,
                "recipient": recipient,
                "subject": subject or "",
                "body_preview": body[:200],
            },
        )
        return ChannelSendResult(
            success=True,
            message=f"Email logged via SMTP stub (from={from_addr}, to={recipient})",
        )

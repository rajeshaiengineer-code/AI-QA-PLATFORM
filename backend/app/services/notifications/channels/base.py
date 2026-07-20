"""Notification channel ports and shared result type."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ChannelSendResult:
    """Outcome of a channel delivery attempt."""

    success: bool
    message: str
    error_message: Optional[str] = None


class NotificationChannelPort(ABC):
    """Port for a single notification delivery channel."""

    name: str

    @abstractmethod
    async def send(
        self,
        *,
        recipient: str,
        subject: Optional[str],
        body: str,
    ) -> ChannelSendResult:
        """Deliver a notification on this channel."""

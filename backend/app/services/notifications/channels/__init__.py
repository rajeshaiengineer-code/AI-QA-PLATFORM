"""Notification channel implementations."""

from app.services.notifications.channels.base import (
    ChannelSendResult,
    NotificationChannelPort,
)
from app.services.notifications.channels.email import EmailChannel
from app.services.notifications.channels.slack import SlackChannel
from app.services.notifications.channels.teams import TeamsChannel

__all__ = [
    "ChannelSendResult",
    "EmailChannel",
    "NotificationChannelPort",
    "SlackChannel",
    "TeamsChannel",
]

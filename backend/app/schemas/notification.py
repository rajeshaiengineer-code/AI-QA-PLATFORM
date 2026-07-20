"""Notification request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import AliasChoices, Field

from app.models.enums import NotificationChannel, NotificationStatus
from app.schemas.base import BaseSchema, PaginatedResponse


class NotificationSendRequest(BaseSchema):
    """Payload for POST /notifications/send."""

    channel: NotificationChannel = Field(
        ...,
        description="Delivery channel: email, slack, or teams",
    )
    recipient: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Email address, Slack channel/user, or Teams webhook override target",
    )
    subject: Optional[str] = Field(
        None,
        max_length=500,
        description="Subject / title (required for email; used as Slack/Teams heading)",
    )
    body: str = Field(..., min_length=1, description="Notification body text")
    persist: Optional[bool] = Field(
        None,
        description="Override NOTIFICATIONS_PERSIST for this send (null = use settings)",
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional caller metadata stored on NotificationLog",
    )


class NotificationLogResponse(BaseSchema):
    """Single notification history row."""

    id: UUID
    channel: NotificationChannel
    recipient: str
    subject: Optional[str] = None
    body: str
    status: NotificationStatus
    error_message: Optional[str] = None
    workflow_run_id: Optional[UUID] = None
    story_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    project_id: Optional[UUID] = None
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        validation_alias=AliasChoices("extra_data", "metadata"),
    )
    created_at: datetime
    updated_at: datetime


class NotificationSendResponse(BaseSchema):
    """Result of a send attempt."""

    success: bool
    channel: NotificationChannel
    recipient: str
    status: NotificationStatus
    message: str
    notification_id: Optional[UUID] = None
    error_message: Optional[str] = None


NotificationListResponse = PaginatedResponse[NotificationLogResponse]

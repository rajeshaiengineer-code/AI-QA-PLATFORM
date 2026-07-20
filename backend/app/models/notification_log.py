"""NotificationLog — audit trail for outbound notification attempts."""

from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.base import BaseEntity
from app.models.enums import NotificationChannel, NotificationStatus


class NotificationLog(BaseEntity):
    """
    Persisted record of a notification send attempt.

    Optional for callers that only need fire-and-forget delivery;
    the notification service writes a row when persistence is enabled.
    """

    channel: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
        default=NotificationChannel.EMAIL.value,
    )
    recipient: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=NotificationStatus.PENDING.value,
        server_default=NotificationStatus.PENDING.value,
        index=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Optional workflow / domain correlation
    workflow_run_id: Mapped[Optional[UUID]] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    story_id: Mapped[Optional[UUID]] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    organization_id: Mapped[Optional[UUID]] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    project_id: Mapped[Optional[UUID]] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    extra_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )

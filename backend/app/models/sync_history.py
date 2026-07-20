"""SyncHistory — records connector synchronization runs."""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.base import BaseEntity


class SyncHistory(BaseEntity):
    """
    Audit trail for connector sync jobs (e.g. Jira import).
    """

    connector_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="running",
        server_default="running",
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    projects_synced: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sprints_synced: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stories_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stories_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stories_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

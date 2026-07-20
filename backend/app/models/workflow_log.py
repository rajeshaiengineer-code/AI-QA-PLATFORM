"""WorkflowLog — durable log of transitions and engine actions."""

from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import BaseEntity

if TYPE_CHECKING:
    from app.models.workflow_run import WorkflowRun


class WorkflowLog(BaseEntity):
    """Append-only style log entry for a workflow run."""

    run_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="info",
        server_default="info",
    )
    event_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    from_state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)

    run: Mapped["WorkflowRun"] = relationship(
        "WorkflowRun",
        back_populates="logs",
    )

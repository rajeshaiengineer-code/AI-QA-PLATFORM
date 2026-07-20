"""AutomationJob domain model — batch automation run."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import BaseEntity
from app.models.enums import AutomationStatus
from app.models.types import automation_status_enum

if TYPE_CHECKING:
    from app.models.execution import Execution
    from app.models.project import Project
    from app.models.sprint import Sprint


class AutomationJob(BaseEntity):
    """
    Batch automation run for a project (optionally scoped to a sprint).

    Owns many Executions — one per test case included in the run.
    """

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sprint_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("sprints.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[AutomationStatus] = mapped_column(
        automation_status_enum,
        nullable=False,
        default=AutomationStatus.PENDING,
        server_default=AutomationStatus.PENDING.value,
        index=True,
    )
    triggered_by: Mapped[Optional[UUID]] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        doc="Actor UUID that triggered the job (User FK deferred).",
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    config: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Run configuration (browser, environment, tags, story/artifact ids, etc.).",
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="automation_jobs",
    )
    sprint: Mapped[Optional["Sprint"]] = relationship(
        "Sprint",
        back_populates="automation_jobs",
    )
    executions: Mapped[List["Execution"]] = relationship(
        "Execution",
        back_populates="automation_job",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

"""Sprint domain model — time-boxed delivery iteration."""

from datetime import date
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import Boolean, Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseEntity

if TYPE_CHECKING:
    from app.models.automation_job import AutomationJob
    from app.models.project import Project
    from app.models.story import Story


class Sprint(BaseEntity):
    """
    Time-boxed iteration within a project.

    Stories may optionally belong to a sprint; unassigned stories remain in backlog.
    """

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    external_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="External system id (e.g. Jira sprint id).",
    )
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="sprints",
    )
    stories: Mapped[List["Story"]] = relationship(
        "Story",
        back_populates="sprint",
        lazy="selectin",
    )
    automation_jobs: Mapped[List["AutomationJob"]] = relationship(
        "AutomationJob",
        back_populates="sprint",
        lazy="selectin",
    )

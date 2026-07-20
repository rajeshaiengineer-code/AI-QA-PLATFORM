"""Bug domain model — defect found during testing or reported against a story."""

from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import BaseEntity
from app.models.enums import BugStatus, Priority
from app.models.types import bug_status_enum, priority_enum

if TYPE_CHECKING:
    from app.models.execution import Execution
    from app.models.failure_analysis import FailureAnalysis
    from app.models.project import Project
    from app.models.story import Story
    from app.models.test_case import TestCase


class Bug(BaseEntity):
    """
    Defect tracked against a project, optionally linked to story/test/execution.

    Supports both failure-driven filing (from Execution) and manual reporting.
    """

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    story_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("stories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    test_case_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("test_cases.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    execution_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("executions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    failure_analysis_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("failure_analyses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[BugStatus] = mapped_column(
        bug_status_enum,
        nullable=False,
        default=BugStatus.OPEN,
        server_default=BugStatus.OPEN.value,
        index=True,
    )
    priority: Mapped[Priority] = mapped_column(
        priority_enum,
        nullable=False,
        default=Priority.MEDIUM,
        server_default=Priority.MEDIUM.value,
        index=True,
    )
    external_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="External tracker key (e.g. Jira bug key).",
    )
    extra_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "extra_metadata",
        JSON,
        nullable=True,
        doc="Attachment links / context (summary, logs, execution URLs, Jira).",
    )

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="bugs",
    )
    story: Mapped[Optional["Story"]] = relationship(
        "Story",
        back_populates="bugs",
    )
    test_case: Mapped[Optional["TestCase"]] = relationship(
        "TestCase",
        back_populates="bugs",
    )
    execution: Mapped[Optional["Execution"]] = relationship(
        "Execution",
        back_populates="bugs",
    )
    failure_analysis: Mapped[Optional["FailureAnalysis"]] = relationship(
        "FailureAnalysis",
        back_populates="bugs",
    )

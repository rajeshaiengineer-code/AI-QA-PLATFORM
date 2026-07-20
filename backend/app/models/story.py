"""Story domain model — requirement / user story work item."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import BaseEntity
from app.models.enums import Priority, StoryStatus, StoryType
from app.models.types import priority_enum, story_status_enum, story_type_enum

if TYPE_CHECKING:
    from app.models.acceptance_criteria import AcceptanceCriteria
    from app.models.automation_artifact import AutomationArtifact
    from app.models.bdd_feature import BddFeature
    from app.models.bug import Bug
    from app.models.project import Project
    from app.models.sprint import Sprint
    from app.models.story_analysis import StoryAnalysis
    from app.models.test_case import TestCase


class Story(BaseEntity):
    """
    User story or work item that drives test generation.

    Belongs to a project; optionally planned into a sprint.
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
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[StoryStatus] = mapped_column(
        story_status_enum,
        nullable=False,
        default=StoryStatus.DRAFT,
        server_default=StoryStatus.DRAFT.value,
        index=True,
    )
    story_type: Mapped[StoryType] = mapped_column(
        story_type_enum,
        nullable=False,
        default=StoryType.FEATURE,
        server_default=StoryType.FEATURE.value,
    )
    priority: Mapped[Priority] = mapped_column(
        priority_enum,
        nullable=False,
        default=Priority.MEDIUM,
        server_default=Priority.MEDIUM.value,
        index=True,
    )
    story_points: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    external_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="External tracker key (e.g. Jira issue key).",
    )
    jira_issue_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Stable Jira issue id for sync (not the key).",
    )
    labels: Mapped[Optional[List[Any]]] = mapped_column(JSON, nullable=True)
    assignee: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reporter: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    external_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Source system updated timestamp for change detection.",
    )
    rank: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Ordering within backlog or sprint.",
    )

    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="stories",
    )
    sprint: Mapped[Optional["Sprint"]] = relationship(
        "Sprint",
        back_populates="stories",
    )
    acceptance_criteria: Mapped[List["AcceptanceCriteria"]] = relationship(
        "AcceptanceCriteria",
        back_populates="story",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    test_cases: Mapped[List["TestCase"]] = relationship(
        "TestCase",
        back_populates="story",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    bugs: Mapped[List["Bug"]] = relationship(
        "Bug",
        back_populates="story",
        lazy="selectin",
    )
    analyses: Mapped[List["StoryAnalysis"]] = relationship(
        "StoryAnalysis",
        back_populates="story",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    bdd_features: Mapped[List["BddFeature"]] = relationship(
        "BddFeature",
        back_populates="story",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    automation_artifacts: Mapped[List["AutomationArtifact"]] = relationship(
        "AutomationArtifact",
        back_populates="story",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

"""Project domain model — product/application under an organization."""

from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseEntity

if TYPE_CHECKING:
    from app.models.automation_job import AutomationJob
    from app.models.bug import Bug
    from app.models.organization import Organization
    from app.models.sprint import Sprint
    from app.models.story import Story


class Project(BaseEntity):
    """
    Product or application container for QA work.

    Groups sprints, stories, automation jobs, and bugs within an organization.
    """

    __table_args__ = (
        UniqueConstraint("organization_id", "key", name="uq_projects_organization_id_key"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    external_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="External system id (e.g. Jira project id).",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="projects",
    )
    sprints: Mapped[List["Sprint"]] = relationship(
        "Sprint",
        back_populates="project",
        lazy="selectin",
    )
    stories: Mapped[List["Story"]] = relationship(
        "Story",
        back_populates="project",
        lazy="selectin",
    )
    automation_jobs: Mapped[List["AutomationJob"]] = relationship(
        "AutomationJob",
        back_populates="project",
        lazy="selectin",
    )
    bugs: Mapped[List["Bug"]] = relationship(
        "Bug",
        back_populates="project",
        lazy="selectin",
    )

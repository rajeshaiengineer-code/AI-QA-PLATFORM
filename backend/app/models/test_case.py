"""TestCase domain model — executable or manual test definition."""

from typing import TYPE_CHECKING, Any, List, Optional
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import BaseEntity
from app.models.enums import (
    Priority,
    TestCaseCategory,
    TestCaseSource,
    TestCaseStatus,
)
from app.models.types import priority_enum

if TYPE_CHECKING:
    from app.models.acceptance_criteria import AcceptanceCriteria
    from app.models.bug import Bug
    from app.models.execution import Execution
    from app.models.story import Story
    from app.models.test_case_version import TestCaseVersion


class TestCase(BaseEntity):
    """
    Test definition derived from a story (and optionally an acceptance criterion).

    May be executed manually or via automation jobs.
    """

    # Prevent pytest from collecting this ORM model as a test class.
    __test__ = False

    story_id: Mapped[UUID] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    acceptance_criteria_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("acceptance_criteria.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preconditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    steps: Mapped[Optional[List[Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Ordered list of step objects: [{action, expected}, ...].",
    )
    expected_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[Priority] = mapped_column(
        priority_enum,
        nullable=False,
        default=Priority.MEDIUM,
        server_default=Priority.MEDIUM.value,
        index=True,
    )
    is_automated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    order_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        default=None,
        doc="QA category, e.g. positive, negative, boundary, api, …",
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=TestCaseSource.MANUAL.value,
        server_default=TestCaseSource.MANUAL.value,
        index=True,
        doc="Origin of the test case: ai, manual, imported.",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=TestCaseStatus.DRAFT.value,
        server_default=TestCaseStatus.DRAFT.value,
        index=True,
        doc="QA review status: draft, pending_review, approved, rejected.",
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Optional reason supplied when status is set to rejected.",
    )
    tags: Mapped[Optional[List[Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Free-form tags (often mirrors category / risk labels).",
    )
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    story: Mapped["Story"] = relationship(
        "Story",
        back_populates="test_cases",
    )
    acceptance_criteria: Mapped[Optional["AcceptanceCriteria"]] = relationship(
        "AcceptanceCriteria",
        back_populates="test_cases",
    )
    executions: Mapped[List["Execution"]] = relationship(
        "Execution",
        back_populates="test_case",
        lazy="selectin",
    )
    bugs: Mapped[List["Bug"]] = relationship(
        "Bug",
        back_populates="test_case",
        lazy="selectin",
    )
    versions: Mapped[List["TestCaseVersion"]] = relationship(
        "TestCaseVersion",
        back_populates="test_case",
        lazy="selectin",
        order_by="TestCaseVersion.version_number.desc()",
    )

    def category_enum(self) -> Optional[TestCaseCategory]:
        if not self.category:
            return None
        try:
            return TestCaseCategory(self.category)
        except ValueError:
            return None

    def status_enum(self) -> Optional[TestCaseStatus]:
        try:
            return TestCaseStatus(self.status)
        except ValueError:
            return None

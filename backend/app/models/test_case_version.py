"""TestCaseVersion — immutable snapshot of a test case before an edit."""

from typing import TYPE_CHECKING, Any, List, Optional
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import BaseEntity
from app.models.enums import Priority
from app.models.types import priority_enum

if TYPE_CHECKING:
    from app.models.test_case import TestCase


class TestCaseVersion(BaseEntity):
    """
    Point-in-time snapshot of editable TestCase fields.

    Created before each content update so reviewers can inspect history.
    Soft-delete / optimistic-lock columns come from BaseEntity but versions
    are treated as append-only in the service layer.
    """

    test_case_id: Mapped[UUID] = mapped_column(
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="1-based content version at the time of the snapshot.",
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preconditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    steps: Mapped[Optional[List[Any]]] = mapped_column(JSON, nullable=True)
    expected_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[Priority] = mapped_column(
        priority_enum,
        nullable=False,
        default=Priority.MEDIUM,
        server_default=Priority.MEDIUM.value,
    )
    is_automated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tags: Mapped[Optional[List[Any]]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Status of the test case when this snapshot was taken.",
    )
    change_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    test_case: Mapped["TestCase"] = relationship(
        "TestCase",
        back_populates="versions",
    )

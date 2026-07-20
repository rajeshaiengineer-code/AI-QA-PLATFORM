"""AcceptanceCriteria domain model — conditions that define story done-ness."""

from typing import TYPE_CHECKING, List
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseEntity

if TYPE_CHECKING:
    from app.models.story import Story
    from app.models.test_case import TestCase


class AcceptanceCriteria(BaseEntity):
    """
    Measurable acceptance condition for a story.

    Primary input for AI-assisted test case generation.
    """

    story_id: Mapped[UUID] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    is_fulfilled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    story: Mapped["Story"] = relationship(
        "Story",
        back_populates="acceptance_criteria",
    )
    test_cases: Mapped[List["TestCase"]] = relationship(
        "TestCase",
        back_populates="acceptance_criteria",
        lazy="selectin",
    )

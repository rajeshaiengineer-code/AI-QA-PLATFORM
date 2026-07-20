"""StoryAnalysis — persisted AI analysis output for a user story."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import BaseEntity
from app.models.enums import ComplexityLevel, RiskLevel

if TYPE_CHECKING:
    from app.models.story import Story


class StoryAnalysis(BaseEntity):
    """
    Result of running the Story Analyzer against a story.

    Multiple analyses may exist per story; APIs return the latest by created_at.
    """

    story_id: Mapped[UUID] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    complexity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ComplexityLevel.MEDIUM.value,
        server_default=ComplexityLevel.MEDIUM.value,
    )
    risk: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=RiskLevel.MEDIUM.value,
        server_default=RiskLevel.MEDIUM.value,
    )
    automation_candidate: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    dependencies: Mapped[Optional[List[Any]]] = mapped_column(JSON, nullable=True)
    suggested_tests: Mapped[Optional[List[Any]]] = mapped_column(JSON, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_response: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    story: Mapped["Story"] = relationship(
        "Story",
        back_populates="analyses",
    )

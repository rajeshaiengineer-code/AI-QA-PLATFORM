"""BddFeature — persisted Gherkin feature artifact for a story."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import BaseEntity

if TYPE_CHECKING:
    from app.models.story import Story


class BddFeature(BaseEntity):
    """
    Gherkin feature file generated from approved (or draft) test cases.

    Multiple generations may exist per story; list APIs return newest first.
    """

    story_id: Mapped[UUID] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Feature title (Feature: …).",
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gherkin_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Full .feature file text (Feature / Scenario / Outline / Examples / Tags).",
    )
    tags: Mapped[Optional[List[Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Feature-level tags, e.g. ['@smoke', '@auth'].",
    )
    scenarios: Mapped[Optional[List[Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Structured scenarios (scenario / scenario_outline + examples).",
    )
    source_test_case_ids: Mapped[Optional[List[Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="UUIDs of test cases used as generation input.",
    )
    include_drafts: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        doc="Whether draft/pending_review cases were included in generation.",
    )
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_response: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    story: Mapped["Story"] = relationship(
        "Story",
        back_populates="bdd_features",
    )

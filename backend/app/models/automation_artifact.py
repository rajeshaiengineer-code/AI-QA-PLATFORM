"""AutomationArtifact — persisted Playwright TypeScript automation suite for a story."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import BaseEntity

if TYPE_CHECKING:
    from app.models.story import Story


class AutomationArtifact(BaseEntity):
    """
    Playwright TypeScript automation generated from BDD features and/or test cases.

    Each generation stores structured file groups (page objects, locators, fixtures,
    utilities, assertions, hooks, specs) as JSON arrays of
    ``{path, content, description?}`` objects. Multiple generations may exist per
    story; list APIs return newest first.
    """

    story_id: Mapped[UUID] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Suite / package name for the generated automation.",
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="typescript",
        server_default="typescript",
    )
    framework: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="playwright",
        server_default="playwright",
    )
    page_objects: Mapped[Optional[List[Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="[{path, content, description?}]",
    )
    locators: Mapped[Optional[List[Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="[{path, content, description?}]",
    )
    fixtures: Mapped[Optional[List[Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="[{path, content, description?}]",
    )
    utilities: Mapped[Optional[List[Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="[{path, content, description?}]",
    )
    assertions: Mapped[Optional[List[Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="[{path, content, description?}]",
    )
    hooks: Mapped[Optional[List[Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="[{path, content, description?}]",
    )
    specs: Mapped[Optional[List[Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Playwright *.spec.ts files [{path, content, description?}].",
    )
    source_bdd_feature_ids: Mapped[Optional[List[Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="UUIDs of BDD features used as generation input.",
    )
    source_test_case_ids: Mapped[Optional[List[Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="UUIDs of test cases used as generation input.",
    )
    use_bdd: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    use_test_cases: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    include_drafts: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        doc="Whether draft/pending_review cases were included.",
    )
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_response: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    story: Mapped["Story"] = relationship(
        "Story",
        back_populates="automation_artifacts",
    )

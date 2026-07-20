"""FailureAnalysis — persisted AI analysis of a failed execution."""

from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.models.base import BaseEntity
from app.models.enums import FailureCategory

if TYPE_CHECKING:
    from app.models.bug import Bug
    from app.models.execution import Execution


class FailureAnalysis(BaseEntity):
    """
    Result of running AI Failure Analysis against a failed Execution.

    Multiple analyses may exist per execution; APIs return the latest by created_at.
    """

    execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=FailureCategory.UNKNOWN.value,
        server_default=FailureCategory.UNKNOWN.value,
        index=True,
    )
    is_flaky: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    is_product_bug: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_fix: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logs: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Optional logs text or stub path/URL from the analysis request.",
    )
    screenshot_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    video_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    network_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    trace_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_response: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    execution: Mapped["Execution"] = relationship(
        "Execution",
        back_populates="failure_analyses",
    )
    bugs: Mapped[list["Bug"]] = relationship(
        "Bug",
        back_populates="failure_analysis",
        lazy="selectin",
    )

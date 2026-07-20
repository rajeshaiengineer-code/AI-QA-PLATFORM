"""Execution domain model — single test case run result."""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseEntity
from app.models.enums import ExecutionStatus
from app.models.types import execution_status_enum

if TYPE_CHECKING:
    from app.models.automation_job import AutomationJob
    from app.models.bug import Bug
    from app.models.failure_analysis import FailureAnalysis
    from app.models.test_case import TestCase


class Execution(BaseEntity):
    """
    Result of executing one test case within an automation job.

    Captures pass/fail outcome, timing, and failure evidence.
    """

    automation_job_id: Mapped[UUID] = mapped_column(
        ForeignKey("automation_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    test_case_id: Mapped[UUID] = mapped_column(
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[ExecutionStatus] = mapped_column(
        execution_status_enum,
        nullable=False,
        default=ExecutionStatus.PENDING,
        server_default=ExecutionStatus.PENDING.value,
        index=True,
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stack_trace: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        doc="URL/path to screenshot, video, or artifact.",
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    automation_job: Mapped["AutomationJob"] = relationship(
        "AutomationJob",
        back_populates="executions",
    )
    test_case: Mapped["TestCase"] = relationship(
        "TestCase",
        back_populates="executions",
    )
    bugs: Mapped[List["Bug"]] = relationship(
        "Bug",
        back_populates="execution",
        lazy="selectin",
    )
    failure_analyses: Mapped[List["FailureAnalysis"]] = relationship(
        "FailureAnalysis",
        back_populates="execution",
        lazy="selectin",
    )

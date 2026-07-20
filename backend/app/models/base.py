"""
Base Entity Module

Provides the shared SQLAlchemy 2.0 declarative base entity used by all
domain models: UUID PK, audit fields, soft delete, and optimistic locking.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Integer, Uuid, func, text
from sqlalchemy.orm import Mapped, declared_attr, mapped_column

from app.core.database import Base


class BaseEntity(Base):
    """
    Abstract base entity for all domain tables.

    Fields:
        id: UUID primary key
        created_at / updated_at: audit timestamps (UTC)
        created_by / updated_by: actor UUIDs (optional; linked to auth Users)
        is_deleted: soft-delete flag
        version: optimistic concurrency control column
    """

    __abstract__ = True

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    created_by: Mapped[Optional[UUID]] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    updated_by: Mapped[Optional[UUID]] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    __mapper_args__ = {"version_id_col": version}

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Generate plural snake_case table name from the class name."""
        name = cls.__name__
        snake = "".join(
            ["_" + c.lower() if c.isupper() else c for c in name]
        ).lstrip("_")

        # Irregular / explicit plurals for domain clarity
        irregular = {
            "story": "stories",
            "acceptance_criteria": "acceptance_criteria",
            "test_case": "test_cases",
            "automation_job": "automation_jobs",
            "execution": "executions",
            "bug": "bugs",
            "organization": "organizations",
            "project": "projects",
            "sprint": "sprints",
            "sync_history": "sync_histories",
            "story_analysis": "story_analyses",
            "workflow_run": "workflow_runs",
            "workflow_log": "workflow_logs",
            "test_case_version": "test_case_versions",
            "bdd_feature": "bdd_features",
            "automation_artifact": "automation_artifacts",
            "failure_analysis": "failure_analyses",
            "user": "users",
            "organization_membership": "organization_memberships",
            "notification_log": "notification_logs",
        }
        return irregular.get(snake, f"{snake}s")

    def to_dict(self) -> dict[str, Any]:
        """Convert model columns to a plain dictionary."""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"

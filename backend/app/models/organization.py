"""Organization domain model — multi-tenant root."""

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseEntity

if TYPE_CHECKING:
    from app.models.organization_membership import OrganizationMembership
    from app.models.project import Project


class Organization(BaseEntity):
    """
    Tenant boundary for the platform.

    An organization owns projects and isolates data across customers/teams.
    """

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="organization",
        lazy="selectin",
    )
    memberships: Mapped[List["OrganizationMembership"]] = relationship(
        "OrganizationMembership",
        back_populates="organization",
        lazy="select",
    )

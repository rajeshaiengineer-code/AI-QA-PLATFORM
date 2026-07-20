"""Organization membership — user ↔ organization with RBAC role."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseEntity
from app.models.enums import OrganizationRole

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class OrganizationMembership(BaseEntity):
    """
    Links a User to an Organization with a single role.

    Roles: admin, qa, engineer, viewer.
    """

    user_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default=OrganizationRole.VIEWER.value,
        server_default=OrganizationRole.VIEWER.value,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="memberships",
        lazy="selectin",
    )
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="memberships",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "organization_id",
            name="uq_org_membership_user_org",
        ),
    )

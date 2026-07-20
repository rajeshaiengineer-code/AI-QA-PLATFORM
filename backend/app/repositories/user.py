"""User and organization-membership repositories."""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload, selectinload

from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Async data-access for User entities."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_email(
        self,
        email: str,
        *,
        include_deleted: bool = False,
    ) -> Optional[User]:
        stmt = (
            select(User)
            .options(
                selectinload(User.memberships).selectinload(
                    OrganizationMembership.organization
                )
            )
            .where(User.email == email.lower())
        )
        if not include_deleted:
            stmt = stmt.where(User.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_memberships(
        self,
        user_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Optional[User]:
        stmt = (
            select(User)
            .options(
                selectinload(User.memberships).selectinload(
                    OrganizationMembership.organization
                )
            )
            .where(User.id == user_id)
        )
        if not include_deleted:
            stmt = stmt.where(User.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class OrganizationMembershipRepository(BaseRepository[OrganizationMembership]):
    """Async data-access for organization memberships."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OrganizationMembership)

    async def list_for_user(self, user_id: UUID) -> List[OrganizationMembership]:
        stmt = (
            select(OrganizationMembership)
            .options(
                selectinload(OrganizationMembership.organization),
                noload(OrganizationMembership.user),
            )
            .where(
                OrganizationMembership.user_id == user_id,
                OrganizationMembership.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_membership(
        self,
        user_id: UUID,
        organization_id: UUID,
    ) -> Optional[OrganizationMembership]:
        stmt = select(OrganizationMembership).where(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def organization_exists(self, organization_id: UUID) -> bool:
        stmt = select(Organization.id).where(
            Organization.id == organization_id,
            Organization.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def slug_exists(self, slug: str) -> bool:
        stmt = select(Organization.id).where(
            Organization.slug == slug,
            Organization.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

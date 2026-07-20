"""Authentication service — register, login, refresh, profile."""

from typing import List, Optional
from uuid import UUID

from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    UnauthorizedException,
)
from app.core.security import (
    TOKEN_TYPE_REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import OrganizationRole
from app.models.organization import Organization
from app.models.organization_membership import OrganizationMembership
from app.models.user import User
from app.repositories.user import OrganizationMembershipRepository, UserRepository
from app.schemas.auth import (
    LoginRequest,
    MembershipResponse,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)


class AuthService:
    """Business logic for authentication and user profile."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.memberships = OrganizationMembershipRepository(session)

    def _membership_to_response(
        self,
        membership: OrganizationMembership,
    ) -> MembershipResponse:
        org = membership.organization
        return MembershipResponse(
            id=membership.id,
            organization_id=membership.organization_id,
            organization_name=org.name if org is not None else None,
            organization_slug=org.slug if org is not None else None,
            role=OrganizationRole(membership.role),
        )

    def _user_to_response(self, user: User) -> UserResponse:
        memberships = [
            self._membership_to_response(m)
            for m in (user.memberships or [])
            if not m.is_deleted
        ]
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            memberships=memberships,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def _token_response(self, user: User) -> TokenResponse:
        return TokenResponse(
            access_token=create_access_token(user.id),
            refresh_token=create_refresh_token(user.id),
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=self._user_to_response(user),
        )

    async def register(self, payload: RegisterRequest) -> TokenResponse:
        email = payload.email.lower().strip()
        existing = await self.users.get_by_email(email)
        if existing is not None:
            raise ConflictException(f"User with email '{email}' already exists")

        if payload.organization_id and payload.organization_name:
            raise BadRequestException(
                "Provide either organization_id or organization_name, not both"
            )

        if payload.organization_name and not payload.organization_slug:
            raise BadRequestException(
                "organization_slug is required when creating an organization"
            )

        user = User(
            email=email,
            hashed_password=hash_password(payload.password),
            full_name=payload.full_name.strip(),
            is_active=True,
            is_superuser=False,
        )
        await self.users.add(user)

        if payload.organization_name and payload.organization_slug:
            slug = payload.organization_slug.strip().lower()
            if await self.memberships.slug_exists(slug):
                raise ConflictException(f"Organization slug '{slug}' already exists")
            org = Organization(
                name=payload.organization_name.strip(),
                slug=slug,
                description=None,
                is_active=True,
            )
            self.session.add(org)
            await self.session.flush()
            membership = OrganizationMembership(
                user_id=user.id,
                organization_id=org.id,
                role=OrganizationRole.ADMIN.value,
            )
            await self.memberships.add(membership)
        elif payload.organization_id is not None:
            if not await self.memberships.organization_exists(payload.organization_id):
                raise BadRequestException(
                    f"Organization '{payload.organization_id}' does not exist"
                )
            membership = OrganizationMembership(
                user_id=user.id,
                organization_id=payload.organization_id,
                role=OrganizationRole.VIEWER.value,
            )
            await self.memberships.add(membership)

        await self.session.commit()
        refreshed = await self.users.get_by_id_with_memberships(user.id)
        assert refreshed is not None
        return self._token_response(refreshed)

    async def login(self, payload: LoginRequest) -> TokenResponse:
        email = payload.email.lower().strip()
        user = await self.users.get_by_email(email)
        if user is None or not verify_password(payload.password, user.hashed_password):
            raise UnauthorizedException("Invalid email or password")
        if not user.is_active:
            raise UnauthorizedException("User account is inactive")
        return self._token_response(user)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        try:
            payload = decode_token(refresh_token, expected_type=TOKEN_TYPE_REFRESH)
        except JWTError as exc:
            raise UnauthorizedException("Invalid or expired refresh token") from exc

        subject = payload.get("sub")
        if not subject:
            raise UnauthorizedException("Invalid refresh token")

        try:
            user_id = UUID(str(subject))
        except ValueError as exc:
            raise UnauthorizedException("Invalid refresh token") from exc

        user = await self.users.get_by_id_with_memberships(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedException("User not found or inactive")
        return self._token_response(user)

    async def get_me(self, user_id: UUID) -> UserResponse:
        user = await self.users.get_by_id_with_memberships(user_id)
        if user is None:
            raise UnauthorizedException("User not found")
        return self._user_to_response(user)

    async def get_user_role(
        self,
        user_id: UUID,
        organization_id: UUID,
    ) -> Optional[OrganizationRole]:
        membership = await self.memberships.get_membership(user_id, organization_id)
        if membership is None:
            return None
        return OrganizationRole(membership.role)

    def roles_for_user(self, user: User) -> List[OrganizationRole]:
        return [
            OrganizationRole(m.role)
            for m in (user.memberships or [])
            if not m.is_deleted
        ]

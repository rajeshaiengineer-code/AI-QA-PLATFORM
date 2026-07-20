"""
RBAC FastAPI dependencies.

AUTH_ENABLED=False (default): auth checks are skipped so existing tests
and open local development keep working.

AUTH_ENABLED=True: Bearer JWT access tokens are required for protected deps.
"""

from typing import List, Optional, Sequence
from uuid import UUID

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.dependencies import get_db
from app.core.exceptions import ForbiddenException, UnauthorizedException
from app.core.security import TOKEN_TYPE_ACCESS, decode_token
from app.models.enums import OrganizationRole
from app.models.user import User
from app.repositories.user import UserRepository

# auto_error=False so we can return 401 ourselves / skip when AUTH_ENABLED=False
_bearer = HTTPBearer(auto_error=False)

# Role hierarchy for write / elevated operations (highest → lowest)
ROLE_RANK = {
    OrganizationRole.ADMIN: 40,
    OrganizationRole.QA: 30,
    OrganizationRole.ENGINEER: 20,
    OrganizationRole.VIEWER: 10,
}

# Roles allowed to mutate resources when AUTH_ENABLED
WRITE_ROLES: Sequence[OrganizationRole] = (
    OrganizationRole.ADMIN,
    OrganizationRole.QA,
    OrganizationRole.ENGINEER,
)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_bearer),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Optional[User]:
    """
    Resolve the current user from a Bearer access token when present.

    Returns None when no credentials are supplied. Always validates the
    token when credentials are present (even if AUTH_ENABLED is False).
    """
    if credentials is None:
        return None

    try:
        payload = decode_token(credentials.credentials, expected_type=TOKEN_TYPE_ACCESS)
    except JWTError as exc:
        raise UnauthorizedException("Invalid or expired access token") from exc

    subject = payload.get("sub")
    if not subject:
        raise UnauthorizedException("Invalid access token")

    try:
        user_id = UUID(str(subject))
    except ValueError as exc:
        raise UnauthorizedException("Invalid access token") from exc

    repo = UserRepository(db)
    user = await repo.get_by_id_with_memberships(user_id)
    if user is None or not user.is_active:
        raise UnauthorizedException("User not found or inactive")
    return user


async def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional),
    settings: Settings = Depends(get_settings),
) -> Optional[User]:
    """
    Require authentication when AUTH_ENABLED is True.

    When AUTH_ENABLED is False, returns the user if a token was provided,
    otherwise None (anonymous / open mode).
    """
    if not settings.AUTH_ENABLED:
        return user
    if user is None:
        raise UnauthorizedException("Authentication required")
    return user


async def require_auth(
    user: Optional[User] = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> Optional[User]:
    """
    Dependency for protected routes.

    - AUTH_ENABLED=False: always allows (returns optional user)
    - AUTH_ENABLED=True: requires a valid JWT user
    """
    if settings.AUTH_ENABLED and user is None:
        raise UnauthorizedException("Authentication required")
    return user


def require_roles(*allowed_roles: OrganizationRole):
    """
    Factory: require the user to hold at least one of the given roles
    in any organization (or be a superuser).

    When AUTH_ENABLED=False the check is skipped.
    """

    async def _dependency(
        user: Optional[User] = Depends(require_auth),
        settings: Settings = Depends(get_settings),
    ) -> Optional[User]:
        if not settings.AUTH_ENABLED:
            return user
        assert user is not None
        if user.is_superuser:
            return user
        user_roles = {
            OrganizationRole(m.role)
            for m in (user.memberships or [])
            if not m.is_deleted
        }
        if not user_roles.intersection(set(allowed_roles)):
            raise ForbiddenException(
                f"Requires one of roles: {', '.join(r.value for r in allowed_roles)}"
            )
        return user

    return _dependency


async def require_write_access(
    user: Optional[User] = Depends(require_auth),
    settings: Settings = Depends(get_settings),
) -> Optional[User]:
    """
    Protect mutating (write) operations.

    When AUTH_ENABLED=False: no-op.
    When AUTH_ENABLED=True: user must be admin, qa, or engineer (or superuser).
    Viewers are denied.
    """
    if not settings.AUTH_ENABLED:
        return user
    assert user is not None
    if user.is_superuser:
        return user
    user_roles = {
        OrganizationRole(m.role)
        for m in (user.memberships or [])
        if not m.is_deleted
    }
    if not user_roles.intersection(set(WRITE_ROLES)):
        raise ForbiddenException(
            "Write access requires admin, qa, or engineer role"
        )
    return user


def user_has_org_role(
    user: User,
    organization_id: UUID,
    *,
    min_role: OrganizationRole = OrganizationRole.VIEWER,
) -> bool:
    """Check whether user has at least ``min_role`` in the given organization."""
    if user.is_superuser:
        return True
    required = ROLE_RANK[min_role]
    for membership in user.memberships or []:
        if membership.is_deleted:
            continue
        if membership.organization_id != organization_id:
            continue
        try:
            role = OrganizationRole(membership.role)
        except ValueError:
            continue
        if ROLE_RANK.get(role, 0) >= required:
            return True
    return False


def require_org_role(min_role: OrganizationRole = OrganizationRole.VIEWER):
    """
    Factory: require a minimum role within ``organization_id`` query/path param.

    The dependent endpoint must accept ``organization_id: UUID``.
    Skipped when AUTH_ENABLED=False.
    """

    async def _dependency(
        organization_id: UUID,
        user: Optional[User] = Depends(require_auth),
        settings: Settings = Depends(get_settings),
    ) -> Optional[User]:
        if not settings.AUTH_ENABLED:
            return user
        assert user is not None
        if not user_has_org_role(user, organization_id, min_role=min_role):
            raise ForbiddenException(
                f"Requires {min_role.value} (or higher) in this organization"
            )
        return user

    return _dependency

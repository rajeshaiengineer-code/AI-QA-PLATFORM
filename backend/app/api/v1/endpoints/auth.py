"""
Authentication API Endpoints

Register, login, refresh, and current-user profile.
"""

from typing import Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import ErrorResponse, UnauthorizedException
from app.core.rbac import get_current_user_optional
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth import AuthService

router = APIRouter()


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register user",
    description=(
        "Create a new user account. Optionally create an organization "
        "(caller becomes admin) or join an existing organization as viewer. "
        "Returns JWT access + refresh tokens."
    ),
    responses={
        409: {"model": ErrorResponse, "description": "Email or org slug conflict"},
        400: {"model": ErrorResponse, "description": "Bad request"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def register(
    payload: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return await service.register(payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login",
    description="Authenticate with email and password; returns JWT token pair.",
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def login(
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return await service.login(payload)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh tokens",
    description="Exchange a valid refresh token for a new access + refresh pair.",
    responses={
        401: {"model": ErrorResponse, "description": "Invalid refresh token"},
        422: {"model": ErrorResponse, "description": "Validation error"},
    },
)
async def refresh(
    payload: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    return await service.refresh(payload.refresh_token)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Current user",
    description=(
        "Return the authenticated user's profile and organization memberships. "
        "Requires a Bearer access token (even when AUTH_ENABLED is False)."
    ),
    responses={
        401: {"model": ErrorResponse, "description": "Missing or invalid token"},
    },
)
async def me(
    user: Optional[User] = Depends(get_current_user_optional),
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    if user is None:
        raise UnauthorizedException("Authentication required")
    return await service.get_me(user.id)

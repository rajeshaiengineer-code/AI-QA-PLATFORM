"""
Notifications API Endpoints

Send notifications (email / Slack / Teams) and inspect delivery history.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.core.exceptions import ErrorResponse
from app.core.rbac import require_write_access
from app.models.enums import NotificationChannel, NotificationStatus
from app.models.user import User
from app.schemas.notification import (
    NotificationListResponse,
    NotificationSendRequest,
    NotificationSendResponse,
)
from app.services.notifications import NotificationService

router = APIRouter()


def get_notification_service(
    db: AsyncSession = Depends(get_db),
) -> NotificationService:
    return NotificationService(db)


@router.post(
    "/send",
    response_model=NotificationSendResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a notification",
    description=(
        "Deliver a notification on email (SMTP stub / log), Slack webhook, "
        "or Teams webhook. Optionally persists a NotificationLog row."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid channel or payload"},
    },
)
async def send_notification(
    body: NotificationSendRequest,
    service: NotificationService = Depends(get_notification_service),
    _user: Optional[User] = Depends(require_write_access),
) -> NotificationSendResponse:
    return await service.send(body)


@router.get(
    "",
    response_model=NotificationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List notification history",
    description="Return paginated NotificationLog rows (newest first).",
)
async def list_notifications(
    channel: Optional[NotificationChannel] = Query(
        None,
        description="Filter by channel",
    ),
    status_filter: Optional[NotificationStatus] = Query(
        None,
        alias="status",
        description="Filter by delivery status",
    ),
    organization_id: Optional[UUID] = Query(
        None,
        description="Filter by organization",
    ),
    project_id: Optional[UUID] = Query(
        None,
        description="Filter by project",
    ),
    story_id: Optional[UUID] = Query(
        None,
        description="Filter by story",
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Page size"),
    service: NotificationService = Depends(get_notification_service),
) -> NotificationListResponse:
    return await service.list_history(
        channel=channel,
        status=status_filter,
        organization_id=organization_id,
        project_id=project_id,
        story_id=story_id,
        page=page,
        page_size=page_size,
    )

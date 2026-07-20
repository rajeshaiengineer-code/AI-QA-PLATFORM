"""
NotificationLog Repository

Async data-access for notification history.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_log import NotificationLog
from app.repositories.base import BaseRepository


class NotificationLogRepository(BaseRepository[NotificationLog]):
    """Repository for NotificationLog CRUD and filtered history."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, NotificationLog)

    async def list_history(
        self,
        *,
        channel: Optional[str] = None,
        status: Optional[str] = None,
        organization_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        story_id: Optional[UUID] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[Sequence[NotificationLog], int]:
        """Return paginated notification history (newest first)."""
        filters = [NotificationLog.is_deleted.is_(False)]
        if channel is not None:
            filters.append(NotificationLog.channel == channel)
        if status is not None:
            filters.append(NotificationLog.status == status)
        if organization_id is not None:
            filters.append(NotificationLog.organization_id == organization_id)
        if project_id is not None:
            filters.append(NotificationLog.project_id == project_id)
        if story_id is not None:
            filters.append(NotificationLog.story_id == story_id)

        count_stmt = select(func.count()).select_from(NotificationLog).where(*filters)
        total = int((await self.session.execute(count_stmt)).scalar_one())

        offset = max(page - 1, 0) * page_size
        stmt = (
            select(NotificationLog)
            .where(*filters)
            .order_by(NotificationLog.created_at.desc(), NotificationLog.id.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

"""
Dependencies Module

Provides FastAPI dependency injection utilities.
"""

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.config import Settings, get_settings


# ============================================================
# Settings Dependency
# ============================================================

def get_app_settings() -> Settings:
    """
    Dependency for getting application settings.
    
    Usage:
        @router.get("/config")
        async def get_config(settings: Settings = Depends(get_app_settings)):
            return {"app_name": settings.APP_NAME}
    """
    return get_settings()


# ============================================================
# Database Session Dependency
# ============================================================

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session.
    
    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async for session in get_async_session():
        yield session


# ============================================================
# Common Query Parameters
# ============================================================

class PaginationParams:
    """Common pagination parameters."""

    def __init__(
        self,
        page: int = 1,
        page_size: int = 10,
        max_page_size: int = 100,
    ):
        self.page = max(1, page)
        self.page_size = min(max(1, page_size), max_page_size)
        self.offset = (self.page - 1) * self.page_size
        self.limit = self.page_size


def get_pagination(
    page: int = 1,
    page_size: int = 10,
) -> PaginationParams:
    """
    Dependency for pagination parameters.
    
    Usage:
        @router.get("/items")
        async def get_items(pagination: PaginationParams = Depends(get_pagination)):
            items = await service.get_items(
                offset=pagination.offset,
                limit=pagination.limit
            )
    """
    return PaginationParams(page=page, page_size=page_size)


# ============================================================
# Sorting Parameters
# ============================================================

class SortParams:
    """Common sorting parameters."""

    def __init__(
        self,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        allowed_fields: list = None,
    ):
        self.allowed_fields = allowed_fields or ["created_at", "updated_at", "id"]
        self.sort_by = sort_by if sort_by in self.allowed_fields else "created_at"
        self.sort_order = sort_order.lower() if sort_order.lower() in ["asc", "desc"] else "desc"
        self.is_descending = self.sort_order == "desc"


def get_sorting(
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> SortParams:
    """
    Dependency for sorting parameters.
    
    Usage:
        @router.get("/items")
        async def get_items(sorting: SortParams = Depends(get_sorting)):
            items = await service.get_items(
                sort_by=sorting.sort_by,
                descending=sorting.is_descending
            )
    """
    return SortParams(sort_by=sort_by, sort_order=sort_order)

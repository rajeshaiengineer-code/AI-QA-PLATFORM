"""
Base Repository

Shared async data-access helpers for domain repositories.
"""

from typing import Generic, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import BaseEntity

ModelT = TypeVar("ModelT", bound=BaseEntity)


class BaseRepository(Generic[ModelT]):
    """Generic async repository with soft-delete awareness."""

    def __init__(self, session: AsyncSession, model: Type[ModelT]) -> None:
        self.session = session
        self.model = model

    async def get_by_id(
        self,
        entity_id: UUID,
        *,
        include_deleted: bool = False,
    ) -> Optional[ModelT]:
        """Fetch a single entity by primary key."""
        stmt = select(self.model).where(self.model.id == entity_id)
        if not include_deleted:
            stmt = stmt.where(self.model.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add(self, entity: ModelT) -> ModelT:
        """Persist a new entity and flush to obtain defaults."""
        self.session.add(entity)
        await self.session.flush()
        # Refresh only mapped columns to avoid selectin-loading relationships.
        column_keys = [column.key for column in entity.__table__.columns]
        await self.session.refresh(entity, attribute_names=column_keys)
        return entity

    async def delete(self, entity: ModelT, *, soft: bool = True) -> None:
        """Soft-delete by default; hard-delete when soft=False."""
        if soft:
            entity.is_deleted = True
            await self.session.flush()
        else:
            await self.session.delete(entity)
            await self.session.flush()

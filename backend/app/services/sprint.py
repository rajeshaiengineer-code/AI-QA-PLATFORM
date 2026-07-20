"""
Sprint Service

Business orchestration for Sprint CRUD.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.sprint import Sprint
from app.repositories.sprint import SprintRepository
from app.schemas.base import PaginatedResponse
from app.schemas.sprint import SprintCreate, SprintResponse, SprintUpdate


class SprintService:
    """Service layer for Sprint management."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = SprintRepository(session)

    async def list_sprints(
        self,
        *,
        page: int,
        page_size: int,
        project_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse[SprintResponse]:
        offset = (page - 1) * page_size
        sprints, total = await self.repository.list_filtered(
            offset=offset,
            limit=page_size,
            project_id=project_id,
            is_active=is_active,
            search=search,
        )
        items = [SprintResponse.model_validate(s) for s in sprints]
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_sprint(self, sprint_id: UUID) -> SprintResponse:
        sprint = await self.repository.get_by_id(sprint_id)
        if sprint is None:
            raise NotFoundException("Sprint", str(sprint_id))
        return SprintResponse.model_validate(sprint)

    async def create_sprint(self, payload: SprintCreate) -> SprintResponse:
        if not await self.repository.project_exists(payload.project_id):
            raise BadRequestException(
                f"Project '{payload.project_id}' does not exist"
            )

        sprint = Sprint(
            project_id=payload.project_id,
            name=payload.name,
            goal=payload.goal,
            external_id=payload.external_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            is_active=payload.is_active,
        )
        created = await self.repository.add(sprint)
        return SprintResponse.model_validate(created)

    async def update_sprint(
        self,
        sprint_id: UUID,
        payload: SprintUpdate,
    ) -> SprintResponse:
        sprint = await self.repository.get_by_id(sprint_id)
        if sprint is None:
            raise NotFoundException("Sprint", str(sprint_id))

        data = payload.model_dump(exclude_unset=True)

        if "project_id" in data:
            if not await self.repository.project_exists(data["project_id"]):
                raise BadRequestException(
                    f"Project '{data['project_id']}' does not exist"
                )

        start = data.get("start_date", sprint.start_date)
        end = data.get("end_date", sprint.end_date)
        if start and end and end < start:
            raise BadRequestException("end_date must be on or after start_date")

        for field, value in data.items():
            setattr(sprint, field, value)

        await self.session.flush()
        column_keys = [column.key for column in sprint.__table__.columns]
        await self.session.refresh(sprint, attribute_names=column_keys)
        return SprintResponse.model_validate(sprint)

    async def delete_sprint(self, sprint_id: UUID) -> None:
        sprint = await self.repository.get_by_id(sprint_id)
        if sprint is None:
            raise NotFoundException("Sprint", str(sprint_id))
        await self.repository.delete(sprint, soft=True)

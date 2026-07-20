"""
Story Service

Business orchestration for Story CRUD (no AI / Jira).
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.models.enums import Priority, StoryStatus, StoryType
from app.models.story import Story
from app.repositories.story import StoryRepository
from app.schemas.base import PaginatedResponse
from app.schemas.story import StoryCreate, StoryResponse, StoryUpdate


class StoryService:
    """Service layer for Story management."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = StoryRepository(session)

    async def list_stories(
        self,
        *,
        page: int,
        page_size: int,
        status: Optional[StoryStatus] = None,
        story_type: Optional[StoryType] = None,
        priority: Optional[Priority] = None,
        sprint_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        search: Optional[str] = None,
    ) -> PaginatedResponse[StoryResponse]:
        """List stories with pagination, filters, and search."""
        offset = (page - 1) * page_size
        stories, total = await self.repository.list_filtered(
            offset=offset,
            limit=page_size,
            status=status,
            story_type=story_type,
            priority=priority,
            sprint_id=sprint_id,
            project_id=project_id,
            search=search,
        )
        items = [StoryResponse.model_validate(story) for story in stories]
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_story(self, story_id: UUID) -> StoryResponse:
        """Get a single story by id."""
        story = await self.repository.get_by_id(story_id)
        if story is None:
            raise NotFoundException("Story", str(story_id))
        return StoryResponse.model_validate(story)

    async def create_story(self, payload: StoryCreate) -> StoryResponse:
        """Create a new story after validating project/sprint references."""
        await self._validate_project(payload.project_id)
        await self._validate_sprint(payload.sprint_id, payload.project_id)

        story = Story(
            project_id=payload.project_id,
            sprint_id=payload.sprint_id,
            title=payload.title,
            description=payload.description,
            status=payload.status,
            story_type=payload.story_type,
            priority=payload.priority,
            story_points=payload.story_points,
            external_id=payload.external_id,
            rank=payload.rank,
        )
        created = await self.repository.add(story)
        return StoryResponse.model_validate(created)

    async def update_story(self, story_id: UUID, payload: StoryUpdate) -> StoryResponse:
        """Update an existing story."""
        story = await self.repository.get_by_id(story_id)
        if story is None:
            raise NotFoundException("Story", str(story_id))

        data = payload.model_dump(exclude_unset=True)

        project_id = data.get("project_id", story.project_id)
        sprint_id = data["sprint_id"] if "sprint_id" in data else story.sprint_id

        if "project_id" in data:
            await self._validate_project(project_id)
        if "sprint_id" in data or "project_id" in data:
            await self._validate_sprint(sprint_id, project_id)

        for field, value in data.items():
            setattr(story, field, value)

        await self.session.flush()
        column_keys = [column.key for column in story.__table__.columns]
        await self.session.refresh(story, attribute_names=column_keys)
        return StoryResponse.model_validate(story)

    async def delete_story(self, story_id: UUID) -> None:
        """Soft-delete a story."""
        story = await self.repository.get_by_id(story_id)
        if story is None:
            raise NotFoundException("Story", str(story_id))
        await self.repository.delete(story, soft=True)

    async def _validate_project(self, project_id: UUID) -> None:
        if not await self.repository.project_exists(project_id):
            raise BadRequestException(
                message=f"Project with id '{project_id}' not found",
                details={"project_id": str(project_id)},
            )

    async def _validate_sprint(
        self,
        sprint_id: Optional[UUID],
        project_id: UUID,
    ) -> None:
        if sprint_id is None:
            return
        sprint = await self.repository.get_sprint(sprint_id)
        if sprint is None:
            raise BadRequestException(
                message=f"Sprint with id '{sprint_id}' not found",
                details={"sprint_id": str(sprint_id)},
            )
        if sprint.project_id != project_id:
            raise BadRequestException(
                message="Sprint does not belong to the given project",
                details={
                    "sprint_id": str(sprint_id),
                    "project_id": str(project_id),
                    "sprint_project_id": str(sprint.project_id),
                },
            )

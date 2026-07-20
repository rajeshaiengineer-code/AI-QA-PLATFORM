"""
Jira sync service — import projects, sprints, stories + AC with update detection.

By default only issues in the **active sprint** (``sprint in openSprints()``)
are imported.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.connectors.jira.connector import JiraConnector
from app.connectors.jira.constants import JIRA_CONNECTOR_NAME
from app.connectors.jira.mapper import map_issue, map_project, map_sprint
from app.core.exceptions import NotFoundException
from app.models.acceptance_criteria import AcceptanceCriteria
from app.models.organization import Organization
from app.models.project import Project
from app.models.sprint import Sprint
from app.models.story import Story
from app.models.sync_history import SyncHistory


def build_sync_jql(project_key: str, *, active_sprint_only: bool = True) -> str:
    """Build the JQL used to pull issues for a project during sync."""
    key = (project_key or "").strip()
    if active_sprint_only:
        return f'project = "{key}" AND sprint in openSprints() ORDER BY updated DESC'
    return f'project = "{key}" ORDER BY updated DESC'


class JiraSyncService:
    """Orchestrates Jira → platform synchronization."""

    def __init__(self, session: AsyncSession, connector: JiraConnector) -> None:
        self.session = session
        self.connector = connector

    async def sync(
        self,
        *,
        organization_id: UUID,
        project_keys: Optional[List[str]] = None,
        board_id: Optional[str] = None,
        active_sprint_only: bool = True,
    ) -> SyncHistory:
        if not self.connector.is_connected:
            await self.connector.connect()

        org = await self.session.get(Organization, organization_id)
        if org is None or org.is_deleted:
            raise NotFoundException("Organization", str(organization_id))

        history = SyncHistory(
            connector_name=JIRA_CONNECTOR_NAME,
            status="running",
            started_at=datetime.now(timezone.utc),
            details={
                "organization_id": str(organization_id),
                "project_keys": project_keys,
                "board_id": board_id,
                "active_sprint_only": active_sprint_only,
            },
        )
        self.session.add(history)
        await self.session.flush()

        try:
            stats = await self._run_sync(
                organization_id=organization_id,
                project_keys=project_keys,
                board_id=board_id,
                active_sprint_only=active_sprint_only,
            )
            history.status = "completed"
            history.projects_synced = stats["projects_synced"]
            history.sprints_synced = stats["sprints_synced"]
            history.stories_created = stats["stories_created"]
            history.stories_updated = stats["stories_updated"]
            history.stories_skipped = stats["stories_skipped"]
            history.details = {**(history.details or {}), **stats.get("extra", {})}
        except Exception as exc:  # noqa: BLE001
            history.status = "failed"
            history.error_message = str(exc)
            history.completed_at = datetime.now(timezone.utc)
            await self.session.flush()
            raise

        history.completed_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(history)
        return history

    async def _run_sync(
        self,
        *,
        organization_id: UUID,
        project_keys: Optional[List[str]],
        board_id: Optional[str],
        active_sprint_only: bool,
    ) -> Dict[str, Any]:
        jira_projects = await self.connector.list_projects()
        if project_keys:
            allowed = {k.upper() for k in project_keys}
            jira_projects = [
                p for p in jira_projects if (p.get("key") or "").upper() in allowed
            ]

        projects_synced = 0
        sprints_synced = 0
        stories_created = 0
        stories_updated = 0
        stories_skipped = 0
        project_map: Dict[str, Project] = {}
        sprint_map: Dict[str, Sprint] = {}
        active_sprint_names: List[str] = []
        jql_by_project: Dict[str, str] = {}

        sprint_state = "active" if active_sprint_only else None

        for jp in jira_projects:
            project = await self._upsert_project(organization_id, jp)
            project_map[project.key.upper()] = project
            projects_synced += 1

            boards = await self.connector.list_boards(project_key_or_id=project.key)
            if board_id:
                boards = [b for b in boards if str(b.get("id")) == str(board_id)]

            for board in boards:
                jira_sprints = await self.connector.list_sprints(
                    board["id"],
                    state=sprint_state,
                )
                for js in jira_sprints:
                    sprint = await self._upsert_sprint(project, js)
                    if sprint.external_id:
                        sprint_map[sprint.external_id] = sprint
                    if (js.get("state") or "").lower() == "active":
                        name = js.get("name")
                        if name and name not in active_sprint_names:
                            active_sprint_names.append(name)
                    sprints_synced += 1

        ac_field = self.connector.get_config_value("acceptance_criteria_field")
        fields = self.connector.issue_fields()

        for _key, project in project_map.items():
            jql = build_sync_jql(
                project.key,
                active_sprint_only=active_sprint_only,
            )
            jql_by_project[project.key] = jql
            async for issue in self.connector.client.iter_issues(jql, fields=fields):
                mapped = map_issue(issue, acceptance_criteria_field=ac_field)
                result = await self._upsert_story(project, mapped, sprint_map)
                if result == "created":
                    stories_created += 1
                elif result == "updated":
                    stories_updated += 1
                else:
                    stories_skipped += 1

        return {
            "projects_synced": projects_synced,
            "sprints_synced": sprints_synced,
            "stories_created": stories_created,
            "stories_updated": stories_updated,
            "stories_skipped": stories_skipped,
            "extra": {
                "project_count": len(project_map),
                "active_sprint_only": active_sprint_only,
                "active_sprints": active_sprint_names,
                "jql_by_project": jql_by_project,
            },
        }

    async def _upsert_project(
        self,
        organization_id: UUID,
        jira_project: Dict[str, Any],
    ) -> Project:
        data = map_project(jira_project)
        stmt = select(Project).where(
            Project.is_deleted.is_(False),
            Project.organization_id == organization_id,
            (
                (Project.external_id == data["external_id"])
                | (Project.key == data["key"])
            ),
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.name = data["name"]
            existing.description = data.get("description")
            existing.external_id = data["external_id"]
            existing.key = data["key"][:20]
            await self.session.flush()
            return existing

        project = Project(
            organization_id=organization_id,
            name=data["name"],
            key=data["key"][:20],
            description=data.get("description"),
            external_id=data["external_id"],
        )
        self.session.add(project)
        await self.session.flush()
        return project

    async def _upsert_sprint(
        self,
        project: Project,
        jira_sprint: Dict[str, Any],
    ) -> Sprint:
        data = map_sprint(jira_sprint)
        stmt = select(Sprint).where(
            Sprint.is_deleted.is_(False),
            Sprint.project_id == project.id,
            Sprint.external_id == data["external_id"],
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        if existing:
            existing.name = data["name"]
            existing.goal = data.get("goal")
            existing.start_date = data.get("start_date")
            existing.end_date = data.get("end_date")
            existing.is_active = data.get("is_active", True)
            await self.session.flush()
            return existing

        sprint = Sprint(
            project_id=project.id,
            name=data["name"],
            goal=data.get("goal"),
            start_date=data.get("start_date"),
            end_date=data.get("end_date"),
            is_active=data.get("is_active", True),
            external_id=data["external_id"],
        )
        self.session.add(sprint)
        await self.session.flush()
        return sprint

    async def _upsert_story(
        self,
        project: Project,
        mapped: Dict[str, Any],
        sprint_map: Dict[str, Sprint],
    ) -> str:
        stmt = (
            select(Story)
            .options(
                noload(Story.acceptance_criteria),
                noload(Story.test_cases),
                noload(Story.bugs),
                noload(Story.project),
                noload(Story.sprint),
            )
            .where(
                Story.is_deleted.is_(False),
                Story.project_id == project.id,
                (
                    (Story.jira_issue_id == mapped["jira_issue_id"])
                    | (Story.external_id == mapped["external_id"])
                ),
            )
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()

        sprint_id = None
        jira_sprint_id = mapped.get("jira_sprint_id")
        if jira_sprint_id and jira_sprint_id in sprint_map:
            sprint_id = sprint_map[jira_sprint_id].id

        if existing:
            if (
                existing.external_updated_at
                and mapped.get("external_updated_at")
                and mapped["external_updated_at"] <= existing.external_updated_at
            ):
                return "skipped"

            existing.title = mapped["title"]
            existing.description = mapped.get("description")
            existing.status = mapped["status"]
            existing.story_type = mapped["story_type"]
            existing.priority = mapped["priority"]
            existing.labels = mapped.get("labels") or []
            existing.assignee = mapped.get("assignee")
            existing.reporter = mapped.get("reporter")
            existing.external_id = mapped.get("external_id")
            existing.jira_issue_id = mapped.get("jira_issue_id")
            existing.external_updated_at = mapped.get("external_updated_at")
            if sprint_id:
                existing.sprint_id = sprint_id
            await self.session.flush()
            await self._replace_acceptance_criteria(
                existing.id, mapped.get("acceptance_criteria") or []
            )
            return "updated"

        story = Story(
            project_id=project.id,
            sprint_id=sprint_id,
            title=mapped["title"],
            description=mapped.get("description"),
            status=mapped["status"],
            story_type=mapped["story_type"],
            priority=mapped["priority"],
            labels=mapped.get("labels") or [],
            assignee=mapped.get("assignee"),
            reporter=mapped.get("reporter"),
            external_id=mapped.get("external_id"),
            jira_issue_id=mapped.get("jira_issue_id"),
            external_updated_at=mapped.get("external_updated_at"),
        )
        self.session.add(story)
        await self.session.flush()
        await self._replace_acceptance_criteria(
            story.id, mapped.get("acceptance_criteria") or []
        )
        return "created"

    async def _replace_acceptance_criteria(
        self,
        story_id: UUID,
        criteria: List[str],
    ) -> None:
        existing = (
            await self.session.execute(
                select(AcceptanceCriteria).where(
                    AcceptanceCriteria.story_id == story_id,
                    AcceptanceCriteria.is_deleted.is_(False),
                )
            )
        ).scalars().all()
        for row in existing:
            row.is_deleted = True

        for index, text in enumerate(criteria):
            self.session.add(
                AcceptanceCriteria(
                    story_id=story_id,
                    description=text,
                    order_index=index,
                )
            )
        await self.session.flush()

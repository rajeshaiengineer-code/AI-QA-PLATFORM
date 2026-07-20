"""
Async Jira Cloud REST client with pagination, rate-limit, and retry handling.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from app.connectors.exceptions import (
    ConnectorConnectionError,
    ConnectorCredentialError,
)
from app.connectors.jira.constants import (
    DEFAULT_PAGE_SIZE,
    DEFAULT_TIMEOUT_SECONDS,
    JIRA_AGILE_V1,
    JIRA_API_V3,
    MAX_RETRIES,
    RETRY_STATUSES,
)

logger = logging.getLogger(__name__)


class JiraClient:
    """Thin async wrapper over Jira Cloud REST API v3 + Agile API."""

    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.api_token = api_token
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def open(self) -> None:
        if self._client is not None:
            return
        if not self.base_url or not self.email or not self.api_token:
            raise ConnectorCredentialError(
                "Jira base_url, email, and api_token are required"
            )
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            auth=(self.email, self.api_token),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Any:
        await self.open()
        assert self._client is not None

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                response = await self._client.request(
                    method,
                    path,
                    params=params,
                    json=json,
                )
            except httpx.TransportError as exc:
                last_error = exc
                await asyncio.sleep(min(2**attempt, 8))
                continue

            if response.status_code in RETRY_STATUSES:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else min(2**attempt, 16)
                logger.warning(
                    "Jira rate limit / transient error %s on %s %s — retry in %.1fs",
                    response.status_code,
                    method,
                    path,
                    delay,
                )
                await asyncio.sleep(delay)
                last_error = ConnectorConnectionError(
                    f"Jira transient error {response.status_code}",
                    details={"path": path, "status": response.status_code},
                )
                continue

            if response.status_code == 401:
                raise ConnectorCredentialError(
                    "Jira authentication failed — check email and API token",
                    details={"status": 401},
                )

            if response.status_code >= 400:
                raise ConnectorConnectionError(
                    f"Jira API error {response.status_code}: {response.text[:300]}",
                    details={"status": response.status_code, "path": path},
                )

            if response.status_code == 204 or not response.content:
                return None
            return response.json()

        raise ConnectorConnectionError(
            f"Jira request failed after {self.max_retries} retries: {path}",
            details={"error": str(last_error) if last_error else None},
        )

    async def get_myself(self) -> Dict[str, Any]:
        return await self.request("GET", f"{JIRA_API_V3}/myself")

    async def get_server_info(self) -> Dict[str, Any]:
        return await self.request("GET", f"{JIRA_API_V3}/serverInfo")

    async def list_projects(self) -> List[Dict[str, Any]]:
        """Paginate through project search."""
        projects: List[Dict[str, Any]] = []
        start_at = 0
        while True:
            data = await self.request(
                "GET",
                f"{JIRA_API_V3}/project/search",
                params={"startAt": start_at, "maxResults": DEFAULT_PAGE_SIZE},
            )
            batch = data.get("values") or data.get("projects") or []
            projects.extend(batch)
            if data.get("isLast", True) or not batch:
                break
            start_at += len(batch)
        return projects

    async def list_boards(
        self,
        *,
        project_key_or_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        boards: List[Dict[str, Any]] = []
        start_at = 0
        while True:
            params: Dict[str, Any] = {
                "startAt": start_at,
                "maxResults": DEFAULT_PAGE_SIZE,
            }
            if project_key_or_id:
                params["projectKeyOrId"] = project_key_or_id
            data = await self.request(
                "GET",
                f"{JIRA_AGILE_V1}/board",
                params=params,
            )
            batch = data.get("values") or []
            boards.extend(batch)
            if data.get("isLast", True) or not batch:
                break
            start_at += len(batch)
        return boards

    async def list_sprints(
        self,
        board_id: int | str,
        *,
        state: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List sprints for a board.

        ``state`` may be a comma-separated Agile filter, e.g. ``active``,
        ``active,future``, or ``closed``.
        """
        sprints: List[Dict[str, Any]] = []
        start_at = 0
        while True:
            params: Dict[str, Any] = {
                "startAt": start_at,
                "maxResults": DEFAULT_PAGE_SIZE,
            }
            if state:
                params["state"] = state
            data = await self.request(
                "GET",
                f"{JIRA_AGILE_V1}/board/{board_id}/sprint",
                params=params,
            )
            batch = data.get("values") or []
            sprints.extend(batch)
            if data.get("isLast", True) or not batch:
                break
            start_at += len(batch)
        return sprints

    async def iter_issues(
        self,
        jql: str,
        *,
        fields: Optional[List[str]] = None,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Yield issues for a JQL query with cursor pagination.

        Uses ``POST /rest/api/3/search/jql`` (legacy ``/search`` returns 410).
        """
        if not (jql or "").strip():
            raise ConnectorConnectionError("JQL query must not be empty")

        # New search/jql returns only ids unless fields are explicit.
        field_list = list(fields) if fields else [
            "summary",
            "description",
            "status",
            "issuetype",
            "priority",
            "labels",
            "assignee",
            "reporter",
            "created",
            "updated",
            "project",
            "parent",
        ]
        next_page_token: Optional[str] = None
        while True:
            body: Dict[str, Any] = {
                "jql": jql,
                "maxResults": page_size,
                "fields": field_list,
            }
            if next_page_token:
                body["nextPageToken"] = next_page_token

            data = await self.request(
                "POST",
                f"{JIRA_API_V3}/search/jql",
                json=body,
            )
            issues = data.get("issues") or []
            for issue in issues:
                yield issue

            next_page_token = data.get("nextPageToken")
            if not next_page_token or not issues or data.get("isLast"):
                break

    async def timed_myself(self) -> tuple[Dict[str, Any], float]:
        start = time.perf_counter()
        me = await self.get_myself()
        latency_ms = (time.perf_counter() - start) * 1000
        return me, latency_ms

    async def create_issue(
        self,
        *,
        project_key: str,
        summary: str,
        description: Optional[str] = None,
        issue_type: str = "Bug",
        priority_name: Optional[str] = None,
        labels: Optional[List[str]] = None,
        extra_fields: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a Jira issue (typically a Bug).

        ``description`` is plain text converted to Atlassian Document Format.
        """
        fields: Dict[str, Any] = {
            "project": {"key": project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
        }
        if description:
            fields["description"] = self._plain_text_to_adf(description)
        if priority_name:
            fields["priority"] = {"name": priority_name}
        if labels:
            fields["labels"] = list(labels)
        if extra_fields:
            fields.update(extra_fields)

        return await self.request(
            "POST",
            f"{JIRA_API_V3}/issue",
            json={"fields": fields},
        )

    @staticmethod
    def _plain_text_to_adf(text: str) -> Dict[str, Any]:
        """Convert plain / wiki-ish text into a minimal ADF document."""
        paragraphs: List[Dict[str, Any]] = []
        for line in (text or "").splitlines() or [""]:
            paragraphs.append(
                {
                    "type": "paragraph",
                    "content": (
                        [{"type": "text", "text": line}] if line else []
                    ),
                }
            )
        return {
            "type": "doc",
            "version": 1,
            "content": paragraphs or [{"type": "paragraph", "content": []}],
        }

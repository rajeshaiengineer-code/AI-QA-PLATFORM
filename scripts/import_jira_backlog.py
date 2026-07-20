#!/usr/bin/env python3
"""
Import AI QA Platform backlog (Epics + Stories) into a Jira Cloud project.

Required env vars:
  JIRA_BASE_URL   e.g. https://testaiplatform.atlassian.net
  JIRA_EMAIL      Atlassian account email
  JIRA_API_TOKEN  https://id.atlassian.com/manage-profile/security/api-tokens
  JIRA_PROJECT_KEY  e.g. SCRUM

Optional:
  JIRA_BOARD_ID   Scrum/Kanban board id (auto-detected from project if omitted)
  JIRA_DRY_RUN=1  Print planned creates without calling Jira
  JIRA_SKIP_SPRINTS=1  Create issues but do not assign sprints

Usage (from repo root):
  export JIRA_BASE_URL=https://testaiplatform.atlassian.net
  export JIRA_EMAIL=you@example.com
  export JIRA_API_TOKEN=...
  export JIRA_PROJECT_KEY=SCRUM
  backend/venv/bin/python scripts/import_jira_backlog.py
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

ROOT = Path(__file__).resolve().parent
BACKLOG_PATH = ROOT / "jira_backlog.json"
CSV_PATH = ROOT / "jira_backlog_import.csv"


def env(name: str, default: Optional[str] = None) -> str:
    value = os.environ.get(name, default)
    if not value:
        raise SystemExit(f"Missing required env var: {name}")
    return value


def plain_to_adf(text: str) -> Dict[str, Any]:
    paragraphs: List[Dict[str, Any]] = []
    for line in (text or "").splitlines() or [""]:
        paragraphs.append(
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": line}] if line else [],
            }
        )
    return {"type": "doc", "version": 1, "content": paragraphs}


def build_description(item: Dict[str, Any]) -> str:
    lines = [item.get("description") or ""]
    ac = item.get("acceptance_criteria") or []
    if ac:
        lines.append("")
        lines.append("Acceptance Criteria:")
        for i, criterion in enumerate(ac, 1):
            lines.append(f"{i}. {criterion}")
    return "\n".join(lines).strip()


def write_csv(items: List[Dict[str, Any]]) -> None:
    """CSV for Jira External System Import (Issues)."""
    with CSV_PATH.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "Summary",
                "Issue Type",
                "Description",
                "Priority",
                "Labels",
                "Epic Name",
                "Sprint",
            ],
        )
        writer.writeheader()
        epics = sorted({i["epic"] for i in items})
        for epic in epics:
            writer.writerow(
                {
                    "Summary": epic,
                    "Issue Type": "Epic",
                    "Description": f"Epic: {epic}",
                    "Priority": "High",
                    "Labels": "",
                    "Epic Name": epic,
                    "Sprint": "",
                }
            )
        for item in items:
            writer.writerow(
                {
                    "Summary": item["summary"],
                    "Issue Type": "Story",
                    "Description": build_description(item),
                    "Priority": item.get("priority") or "Medium",
                    "Labels": " ".join(item.get("labels") or []),
                    "Epic Name": item["epic"],
                    "Sprint": item.get("sprint") or "",
                }
            )
    print(f"Wrote CSV: {CSV_PATH}")


class JiraImporter:
    def __init__(
        self,
        base_url: str,
        email: str,
        token: str,
        project_key: str,
        *,
        board_id: Optional[str] = None,
        dry_run: bool = False,
        skip_sprints: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.project_key = project_key
        self.board_id = board_id
        self.dry_run = dry_run
        self.skip_sprints = skip_sprints
        self.client = httpx.Client(
            base_url=self.base_url,
            auth=(email, token),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=60.0,
        )
        self.epic_keys: Dict[str, str] = {}
        self.sprint_ids: Dict[str, int] = {}
        self.epic_link_field: Optional[str] = None
        self.uses_parent = False

    def close(self) -> None:
        self.client.close()

    def request(
        self, method: str, path: str, **kwargs: Any
    ) -> httpx.Response:
        for attempt in range(5):
            response = self.client.request(method, path, **kwargs)
            if response.status_code in (429, 502, 503, 504):
                delay = float(response.headers.get("Retry-After", 2**attempt))
                time.sleep(delay)
                continue
            return response
        return response

    def ensure_myself(self) -> None:
        response = self.request("GET", "/rest/api/3/myself")
        if response.status_code != 200:
            raise SystemExit(
                f"Jira auth failed ({response.status_code}): {response.text}"
            )
        me = response.json()
        print(f"Authenticated as {me.get('displayName')} <{me.get('emailAddress')}>")

    def detect_epic_link_mode(self) -> None:
        """Prefer parent (team-managed); else Epic Link custom field."""
        response = self.request("GET", "/rest/api/3/field")
        response.raise_for_status()
        for field in response.json():
            name = (field.get("name") or "").lower()
            if name == "epic link":
                self.epic_link_field = field["id"]
                print(f"Using Epic Link field: {self.epic_link_field}")
                return
        self.uses_parent = True
        print("No Epic Link field found — will use parent (team-managed)")

    def find_existing_issue(self, summary: str, issue_type: str) -> Optional[str]:
        safe = summary.replace("\\", "\\\\").replace('"', '\\"')
        jql = (
            f'project = {self.project_key} AND issuetype = "{issue_type}" '
            f'AND summary = "{safe}"'
        )
        response = self.request(
            "POST",
            "/rest/api/3/search/jql",
            json={"jql": jql, "maxResults": 5, "fields": ["summary", "issuetype"]},
        )
        if response.status_code != 200:
            return None
        for issue in response.json().get("issues", []):
            if issue.get("fields", {}).get("summary") == summary:
                return issue["key"]
        return None

    def create_issue(
        self,
        *,
        summary: str,
        issue_type: str,
        description: str,
        priority: Optional[str] = None,
        labels: Optional[List[str]] = None,
        parent_key: Optional[str] = None,
        epic_name: Optional[str] = None,
    ) -> str:
        existing = self.find_existing_issue(summary, issue_type)
        if existing:
            print(f"  skip existing {issue_type}: {existing} — {summary}")
            return existing

        fields: Dict[str, Any] = {
            "project": {"key": self.project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
            "description": plain_to_adf(description),
        }
        if priority:
            fields["priority"] = {"name": priority}
        if labels:
            fields["labels"] = labels
        if issue_type == "Epic" and epic_name:
            # Company-managed often has "Epic Name" custom field
            # Try common id; ignore if rejected
            fields["customfield_10011"] = epic_name

        if parent_key:
            if self.uses_parent:
                fields["parent"] = {"key": parent_key}
            elif self.epic_link_field:
                fields[self.epic_link_field] = parent_key

        if self.dry_run:
            print(f"  DRY-RUN create {issue_type}: {summary}")
            return f"DRY-{issue_type}-{summary[:20]}"

        response = self.request(
            "POST", "/rest/api/3/issue", json={"fields": fields}
        )
        if response.status_code >= 400 and "customfield_10011" in fields:
            # Retry without Epic Name field
            fields.pop("customfield_10011", None)
            response = self.request(
                "POST", "/rest/api/3/issue", json={"fields": fields}
            )

        if response.status_code >= 400:
            raise SystemExit(
                f"Failed to create {issue_type} '{summary}': "
                f"{response.status_code} {response.text}"
            )
        key = response.json()["key"]
        print(f"  created {issue_type}: {key} — {summary}")
        return key

    def resolve_board(self) -> Optional[str]:
        if self.board_id:
            return self.board_id
        response = self.request(
            "GET",
            "/rest/agile/1.0/board",
            params={"projectKeyOrId": self.project_key},
        )
        if response.status_code != 200:
            print(f"Warning: could not list boards ({response.status_code})")
            return None
        values = response.json().get("values") or []
        if not values:
            print("Warning: no boards found for project")
            return None
        board_id = str(values[0]["id"])
        print(f"Using board {board_id} ({values[0].get('name')})")
        self.board_id = board_id
        return board_id

    def ensure_sprint(self, name: str) -> Optional[int]:
        if self.skip_sprints:
            return None
        board_id = self.resolve_board()
        if not board_id:
            return None
        if name in self.sprint_ids:
            return self.sprint_ids[name]

        # List existing sprints
        start_at = 0
        while True:
            response = self.request(
                "GET",
                f"/rest/agile/1.0/board/{board_id}/sprint",
                params={"startAt": start_at, "maxResults": 50},
            )
            if response.status_code != 200:
                print(f"Warning: list sprints failed: {response.status_code}")
                return None
            data = response.json()
            for sprint in data.get("values") or []:
                self.sprint_ids[sprint["name"]] = int(sprint["id"])
            if data.get("isLast", True):
                break
            start_at += len(data.get("values") or [])

        if name in self.sprint_ids:
            return self.sprint_ids[name]

        if self.dry_run:
            print(f"  DRY-RUN create sprint: {name}")
            self.sprint_ids[name] = -1
            return -1

        response = self.request(
            "POST",
            "/rest/agile/1.0/sprint",
            json={"name": name, "originBoardId": int(board_id)},
        )
        if response.status_code >= 400:
            print(
                f"Warning: could not create sprint '{name}': "
                f"{response.status_code} {response.text}"
            )
            return None
        sprint_id = int(response.json()["id"])
        self.sprint_ids[name] = sprint_id
        print(f"  created sprint: {name} (id={sprint_id})")
        return sprint_id

    def move_to_sprint(self, sprint_id: int, issue_key: str) -> None:
        if self.dry_run or sprint_id < 0:
            return
        response = self.request(
            "POST",
            f"/rest/agile/1.0/sprint/{sprint_id}/issue",
            json={"issues": [issue_key]},
        )
        if response.status_code >= 400:
            print(
                f"  warning: could not move {issue_key} to sprint {sprint_id}: "
                f"{response.status_code} {response.text}"
            )

    def import_backlog(self, items: List[Dict[str, Any]]) -> None:
        self.ensure_myself()
        self.detect_epic_link_mode()

        epics = sorted({i["epic"] for i in items})
        print(f"\nCreating {len(epics)} epics…")
        for epic in epics:
            key = self.create_issue(
                summary=epic,
                issue_type="Epic",
                description=f"Epic: {epic}",
                priority="High",
                epic_name=epic,
            )
            self.epic_keys[epic] = key

        print(f"\nCreating {len(items)} stories…")
        for item in items:
            epic_key = self.epic_keys[item["epic"]]
            key = self.create_issue(
                summary=item["summary"],
                issue_type="Story",
                description=build_description(item),
                priority=item.get("priority"),
                labels=item.get("labels") or [],
                parent_key=epic_key,
            )
            sprint_name = item.get("sprint")
            if sprint_name:
                sprint_id = self.ensure_sprint(sprint_name)
                if sprint_id is not None:
                    self.move_to_sprint(sprint_id, key)

        print("\nDone.")
        print(f"Board: {self.base_url}/jira/software/c/projects/{self.project_key}/boards")


def main() -> None:
    items: List[Dict[str, Any]] = json.loads(BACKLOG_PATH.read_text(encoding="utf-8"))
    write_csv(items)

    if os.environ.get("JIRA_CSV_ONLY") == "1":
        print("JIRA_CSV_ONLY=1 — CSV written, skipping API import.")
        return

    importer = JiraImporter(
        base_url=env("JIRA_BASE_URL"),
        email=env("JIRA_EMAIL"),
        token=env("JIRA_API_TOKEN"),
        project_key=env("JIRA_PROJECT_KEY", "SCRUM"),
        board_id=os.environ.get("JIRA_BOARD_ID"),
        dry_run=os.environ.get("JIRA_DRY_RUN") == "1",
        skip_sprints=os.environ.get("JIRA_SKIP_SPRINTS") == "1",
    )
    try:
        importer.import_backlog(items)
    finally:
        importer.close()


if __name__ == "__main__":
    main()

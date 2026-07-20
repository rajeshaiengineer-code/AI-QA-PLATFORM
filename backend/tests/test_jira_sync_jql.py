"""Unit tests for Jira sync JQL scoping."""

from app.services.jira_sync import build_sync_jql


def test_build_sync_jql_active_sprint_only_default():
    assert (
        build_sync_jql("SCRUM")
        == 'project = "SCRUM" AND sprint in openSprints() ORDER BY updated DESC'
    )


def test_build_sync_jql_full_project():
    assert (
        build_sync_jql("SCRUM", active_sprint_only=False)
        == 'project = "SCRUM" ORDER BY updated DESC'
    )

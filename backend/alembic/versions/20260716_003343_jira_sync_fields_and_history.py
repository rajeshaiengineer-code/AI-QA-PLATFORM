"""jira_sync_fields_and_history

Revision ID: jira_sync_001
Revises: 8b3f648bbfad
Create Date: 2026-07-16 00:33:43.000000+00:00

Adds Jira external ids, story sync fields, and sync_histories table.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "jira_sync_001"
down_revision: Union[str, None] = "8b3f648bbfad"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("external_id", sa.String(length=100), nullable=True))
    op.create_index(op.f("ix_projects_external_id"), "projects", ["external_id"], unique=False)

    op.add_column("sprints", sa.Column("external_id", sa.String(length=100), nullable=True))
    op.create_index(op.f("ix_sprints_external_id"), "sprints", ["external_id"], unique=False)

    op.add_column("stories", sa.Column("jira_issue_id", sa.String(length=100), nullable=True))
    op.add_column("stories", sa.Column("labels", sa.JSON(), nullable=True))
    op.add_column("stories", sa.Column("assignee", sa.String(length=255), nullable=True))
    op.add_column("stories", sa.Column("reporter", sa.String(length=255), nullable=True))
    op.add_column(
        "stories",
        sa.Column("external_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_stories_jira_issue_id"), "stories", ["jira_issue_id"], unique=False)

    op.create_table(
        "sync_histories",
        sa.Column("connector_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="running", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("projects_synced", sa.Integer(), server_default="0", nullable=False),
        sa.Column("sprints_synced", sa.Integer(), server_default="0", nullable=False),
        sa.Column("stories_created", sa.Integer(), server_default="0", nullable=False),
        sa.Column("stories_updated", sa.Integer(), server_default="0", nullable=False),
        sa.Column("stories_skipped", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sync_histories")),
    )
    op.create_index(
        op.f("ix_sync_histories_connector_name"),
        "sync_histories",
        ["connector_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_sync_histories_status"),
        "sync_histories",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_sync_histories_status"), table_name="sync_histories")
    op.drop_index(op.f("ix_sync_histories_connector_name"), table_name="sync_histories")
    op.drop_table("sync_histories")

    op.drop_index(op.f("ix_stories_jira_issue_id"), table_name="stories")
    op.drop_column("stories", "external_updated_at")
    op.drop_column("stories", "reporter")
    op.drop_column("stories", "assignee")
    op.drop_column("stories", "labels")
    op.drop_column("stories", "jira_issue_id")

    op.drop_index(op.f("ix_sprints_external_id"), table_name="sprints")
    op.drop_column("sprints", "external_id")

    op.drop_index(op.f("ix_projects_external_id"), table_name="projects")
    op.drop_column("projects", "external_id")

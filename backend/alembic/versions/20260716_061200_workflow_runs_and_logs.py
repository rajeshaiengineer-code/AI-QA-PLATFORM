"""workflow runs and logs

Revision ID: workflow_001
Revises: jira_sync_001
Create Date: 2026-07-16 06:12:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "workflow_001"
down_revision: Union[str, None] = "jira_sync_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("story_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=True),
        sa.Column("project_id", sa.UUID(), nullable=False),
        sa.Column("state", sa.String(length=50), server_default="new", nullable=False),
        sa.Column("last_event", sa.String(length=80), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_retries", sa.Integer(), server_default="3", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_runs_story_id", "workflow_runs", ["story_id"])
    op.create_index("ix_workflow_runs_organization_id", "workflow_runs", ["organization_id"])
    op.create_index("ix_workflow_runs_project_id", "workflow_runs", ["project_id"])
    op.create_index("ix_workflow_runs_state", "workflow_runs", ["state"])
    op.create_index("ix_workflow_runs_is_deleted", "workflow_runs", ["is_deleted"])

    op.create_table(
        "workflow_logs",
        sa.Column("run_id", sa.UUID(), nullable=False),
        sa.Column("level", sa.String(length=20), server_default="info", nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=True),
        sa.Column("from_state", sa.String(length=50), nullable=True),
        sa.Column("to_state", sa.String(length=50), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("id", sa.UUID(), nullable=False),
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
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["workflow_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_logs_run_id", "workflow_logs", ["run_id"])
    op.create_index("ix_workflow_logs_is_deleted", "workflow_logs", ["is_deleted"])


def downgrade() -> None:
    op.drop_index("ix_workflow_logs_is_deleted", table_name="workflow_logs")
    op.drop_index("ix_workflow_logs_run_id", table_name="workflow_logs")
    op.drop_table("workflow_logs")
    op.drop_index("ix_workflow_runs_is_deleted", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_state", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_project_id", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_organization_id", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_story_id", table_name="workflow_runs")
    op.drop_table("workflow_runs")

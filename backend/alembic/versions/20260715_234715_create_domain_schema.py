"""create_domain_schema

Revision ID: 8b3f648bbfad
Revises:
Create Date: 2026-07-15 23:47:15.520168+00:00

Creates the core QA domain schema:
organizations, projects, sprints, stories, acceptance_criteria,
test_cases, automation_jobs, executions, bugs.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "8b3f648bbfad"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# create_type=False: types are created explicitly in upgrade()/downgrade()
# so create_table does not emit a second CREATE TYPE.
story_status_enum = postgresql.ENUM(
    "draft",
    "ready",
    "in_progress",
    "in_review",
    "done",
    "blocked",
    name="story_status",
    create_type=False,
)
story_type_enum = postgresql.ENUM(
    "feature",
    "bug",
    "task",
    "spike",
    "enhancement",
    name="story_type",
    create_type=False,
)
priority_enum = postgresql.ENUM(
    "critical",
    "high",
    "medium",
    "low",
    name="priority",
    create_type=False,
)
automation_status_enum = postgresql.ENUM(
    "pending",
    "queued",
    "running",
    "completed",
    "failed",
    "cancelled",
    name="automation_status",
    create_type=False,
)
execution_status_enum = postgresql.ENUM(
    "pending",
    "running",
    "passed",
    "failed",
    "skipped",
    "error",
    "blocked",
    name="execution_status",
    create_type=False,
)
bug_status_enum = postgresql.ENUM(
    "open",
    "in_progress",
    "resolved",
    "verified",
    "closed",
    "reopened",
    name="bug_status",
    create_type=False,
)


def upgrade() -> None:
    """Upgrade database schema."""
    bind = op.get_bind()
    story_status_enum.create(bind, checkfirst=True)
    story_type_enum.create(bind, checkfirst=True)
    priority_enum.create(bind, checkfirst=True)
    automation_status_enum.create(bind, checkfirst=True)
    execution_status_enum.create(bind, checkfirst=True)
    bug_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "organizations",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_organizations")),
    )
    op.create_index(op.f("ix_organizations_slug"), "organizations", ["slug"], unique=True)

    op.create_table(
        "projects",
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("key", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
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
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_projects_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_projects")),
        sa.UniqueConstraint(
            "organization_id",
            "key",
            name="uq_projects_organization_id_key",
        ),
    )
    op.create_index(op.f("ix_projects_organization_id"), "projects", ["organization_id"], unique=False)

    op.create_table(
        "sprints",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("goal", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
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
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_sprints_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sprints")),
    )
    op.create_index(op.f("ix_sprints_project_id"), "sprints", ["project_id"], unique=False)

    op.create_table(
        "stories",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("sprint_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            story_status_enum,
            server_default="draft",
            nullable=False,
        ),
        sa.Column(
            "story_type",
            story_type_enum,
            server_default="feature",
            nullable=False,
        ),
        sa.Column(
            "priority",
            priority_enum,
            server_default="medium",
            nullable=False,
        ),
        sa.Column("story_points", sa.Integer(), nullable=True),
        sa.Column("external_id", sa.String(length=100), nullable=True),
        sa.Column("rank", sa.Integer(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_stories_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sprint_id"],
            ["sprints.id"],
            name=op.f("fk_stories_sprint_id_sprints"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stories")),
    )
    op.create_index(op.f("ix_stories_external_id"), "stories", ["external_id"], unique=False)
    op.create_index(op.f("ix_stories_priority"), "stories", ["priority"], unique=False)
    op.create_index(op.f("ix_stories_project_id"), "stories", ["project_id"], unique=False)
    op.create_index(op.f("ix_stories_sprint_id"), "stories", ["sprint_id"], unique=False)
    op.create_index(op.f("ix_stories_status"), "stories", ["status"], unique=False)

    op.create_table(
        "automation_jobs",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("sprint_id", sa.Uuid(), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            automation_status_enum,
            server_default="pending",
            nullable=False,
        ),
        sa.Column("triggered_by", sa.Uuid(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_automation_jobs_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sprint_id"],
            ["sprints.id"],
            name=op.f("fk_automation_jobs_sprint_id_sprints"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_automation_jobs")),
    )
    op.create_index(
        op.f("ix_automation_jobs_project_id"),
        "automation_jobs",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_automation_jobs_sprint_id"),
        "automation_jobs",
        ["sprint_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_automation_jobs_status"),
        "automation_jobs",
        ["status"],
        unique=False,
    )

    op.create_table(
        "acceptance_criteria",
        sa.Column("story_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("order_index", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_fulfilled", sa.Boolean(), server_default="false", nullable=False),
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
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            name=op.f("fk_acceptance_criteria_story_id_stories"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_acceptance_criteria")),
    )
    op.create_index(
        op.f("ix_acceptance_criteria_story_id"),
        "acceptance_criteria",
        ["story_id"],
        unique=False,
    )

    op.create_table(
        "test_cases",
        sa.Column("story_id", sa.Uuid(), nullable=False),
        sa.Column("acceptance_criteria_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("preconditions", sa.Text(), nullable=True),
        sa.Column("steps", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("expected_result", sa.Text(), nullable=True),
        sa.Column(
            "priority",
            priority_enum,
            server_default="medium",
            nullable=False,
        ),
        sa.Column("is_automated", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("order_index", sa.Integer(), server_default="0", nullable=False),
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
        sa.ForeignKeyConstraint(
            ["acceptance_criteria_id"],
            ["acceptance_criteria.id"],
            name=op.f("fk_test_cases_acceptance_criteria_id_acceptance_criteria"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            name=op.f("fk_test_cases_story_id_stories"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_test_cases")),
    )
    op.create_index(
        op.f("ix_test_cases_acceptance_criteria_id"),
        "test_cases",
        ["acceptance_criteria_id"],
        unique=False,
    )
    op.create_index(op.f("ix_test_cases_priority"), "test_cases", ["priority"], unique=False)
    op.create_index(op.f("ix_test_cases_story_id"), "test_cases", ["story_id"], unique=False)

    op.create_table(
        "executions",
        sa.Column("automation_job_id", sa.Uuid(), nullable=False),
        sa.Column("test_case_id", sa.Uuid(), nullable=False),
        sa.Column(
            "status",
            execution_status_enum,
            server_default="pending",
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("stack_trace", sa.Text(), nullable=True),
        sa.Column("evidence_url", sa.String(length=1000), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
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
        sa.ForeignKeyConstraint(
            ["automation_job_id"],
            ["automation_jobs.id"],
            name=op.f("fk_executions_automation_job_id_automation_jobs"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["test_case_id"],
            ["test_cases.id"],
            name=op.f("fk_executions_test_case_id_test_cases"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_executions")),
    )
    op.create_index(
        op.f("ix_executions_automation_job_id"),
        "executions",
        ["automation_job_id"],
        unique=False,
    )
    op.create_index(op.f("ix_executions_status"), "executions", ["status"], unique=False)
    op.create_index(op.f("ix_executions_test_case_id"), "executions", ["test_case_id"], unique=False)

    op.create_table(
        "bugs",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("story_id", sa.Uuid(), nullable=True),
        sa.Column("test_case_id", sa.Uuid(), nullable=True),
        sa.Column("execution_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            bug_status_enum,
            server_default="open",
            nullable=False,
        ),
        sa.Column(
            "priority",
            priority_enum,
            server_default="medium",
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=100), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["executions.id"],
            name=op.f("fk_bugs_execution_id_executions"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_bugs_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            name=op.f("fk_bugs_story_id_stories"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["test_case_id"],
            ["test_cases.id"],
            name=op.f("fk_bugs_test_case_id_test_cases"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bugs")),
    )
    op.create_index(op.f("ix_bugs_execution_id"), "bugs", ["execution_id"], unique=False)
    op.create_index(op.f("ix_bugs_external_id"), "bugs", ["external_id"], unique=False)
    op.create_index(op.f("ix_bugs_priority"), "bugs", ["priority"], unique=False)
    op.create_index(op.f("ix_bugs_project_id"), "bugs", ["project_id"], unique=False)
    op.create_index(op.f("ix_bugs_status"), "bugs", ["status"], unique=False)
    op.create_index(op.f("ix_bugs_story_id"), "bugs", ["story_id"], unique=False)
    op.create_index(op.f("ix_bugs_test_case_id"), "bugs", ["test_case_id"], unique=False)


def downgrade() -> None:
    """Downgrade database schema."""
    op.drop_index(op.f("ix_bugs_test_case_id"), table_name="bugs")
    op.drop_index(op.f("ix_bugs_story_id"), table_name="bugs")
    op.drop_index(op.f("ix_bugs_status"), table_name="bugs")
    op.drop_index(op.f("ix_bugs_project_id"), table_name="bugs")
    op.drop_index(op.f("ix_bugs_priority"), table_name="bugs")
    op.drop_index(op.f("ix_bugs_external_id"), table_name="bugs")
    op.drop_index(op.f("ix_bugs_execution_id"), table_name="bugs")
    op.drop_table("bugs")

    op.drop_index(op.f("ix_executions_test_case_id"), table_name="executions")
    op.drop_index(op.f("ix_executions_status"), table_name="executions")
    op.drop_index(op.f("ix_executions_automation_job_id"), table_name="executions")
    op.drop_table("executions")

    op.drop_index(op.f("ix_test_cases_story_id"), table_name="test_cases")
    op.drop_index(op.f("ix_test_cases_priority"), table_name="test_cases")
    op.drop_index(op.f("ix_test_cases_acceptance_criteria_id"), table_name="test_cases")
    op.drop_table("test_cases")

    op.drop_index(op.f("ix_acceptance_criteria_story_id"), table_name="acceptance_criteria")
    op.drop_table("acceptance_criteria")

    op.drop_index(op.f("ix_automation_jobs_status"), table_name="automation_jobs")
    op.drop_index(op.f("ix_automation_jobs_sprint_id"), table_name="automation_jobs")
    op.drop_index(op.f("ix_automation_jobs_project_id"), table_name="automation_jobs")
    op.drop_table("automation_jobs")

    op.drop_index(op.f("ix_stories_status"), table_name="stories")
    op.drop_index(op.f("ix_stories_sprint_id"), table_name="stories")
    op.drop_index(op.f("ix_stories_project_id"), table_name="stories")
    op.drop_index(op.f("ix_stories_priority"), table_name="stories")
    op.drop_index(op.f("ix_stories_external_id"), table_name="stories")
    op.drop_table("stories")

    op.drop_index(op.f("ix_sprints_project_id"), table_name="sprints")
    op.drop_table("sprints")

    op.drop_index(op.f("ix_projects_organization_id"), table_name="projects")
    op.drop_table("projects")

    op.drop_index(op.f("ix_organizations_slug"), table_name="organizations")
    op.drop_table("organizations")

    bug_status_enum.drop(op.get_bind(), checkfirst=True)
    execution_status_enum.drop(op.get_bind(), checkfirst=True)
    automation_status_enum.drop(op.get_bind(), checkfirst=True)
    priority_enum.drop(op.get_bind(), checkfirst=True)
    story_type_enum.drop(op.get_bind(), checkfirst=True)
    story_status_enum.drop(op.get_bind(), checkfirst=True)

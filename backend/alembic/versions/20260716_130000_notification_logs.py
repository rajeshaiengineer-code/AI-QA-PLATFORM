"""notification_logs table for Notifications milestone

Revision ID: notif_001
Revises: auth_rbac_001
Create Date: 2026-07-16 13:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "notif_001"
down_revision: Union[str, None] = "auth_rbac_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_logs",
        sa.Column("channel", sa.String(length=40), nullable=False),
        sa.Column("recipient", sa.String(length=500), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=40),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("workflow_run_id", sa.Uuid(), nullable=True),
        sa.Column("story_id", sa.Uuid(), nullable=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("extra_data", sa.JSON(), nullable=True),
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
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_notification_logs_channel"),
        "notification_logs",
        ["channel"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_logs_recipient"),
        "notification_logs",
        ["recipient"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_logs_status"),
        "notification_logs",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_logs_workflow_run_id"),
        "notification_logs",
        ["workflow_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_logs_story_id"),
        "notification_logs",
        ["story_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_logs_organization_id"),
        "notification_logs",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notification_logs_project_id"),
        "notification_logs",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_notification_logs_project_id"), table_name="notification_logs")
    op.drop_index(
        op.f("ix_notification_logs_organization_id"),
        table_name="notification_logs",
    )
    op.drop_index(op.f("ix_notification_logs_story_id"), table_name="notification_logs")
    op.drop_index(
        op.f("ix_notification_logs_workflow_run_id"),
        table_name="notification_logs",
    )
    op.drop_index(op.f("ix_notification_logs_status"), table_name="notification_logs")
    op.drop_index(op.f("ix_notification_logs_recipient"), table_name="notification_logs")
    op.drop_index(op.f("ix_notification_logs_channel"), table_name="notification_logs")
    op.drop_table("notification_logs")

"""test case status and versions

Revision ID: qa_approval_001
Revises: test_case_gen_001
Create Date: 2026-07-16 08:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "qa_approval_001"
down_revision: Union[str, None] = "test_case_gen_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "test_cases",
        sa.Column(
            "status",
            sa.String(length=50),
            server_default="draft",
            nullable=False,
        ),
    )
    op.add_column(
        "test_cases",
        sa.Column("rejection_reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_test_cases_status", "test_cases", ["status"])

    # AI-generated cases awaiting review should start in pending_review.
    op.execute(
        "UPDATE test_cases SET status = 'pending_review' "
        "WHERE source = 'ai' AND status = 'draft'"
    )

    op.create_table(
        "test_case_versions",
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
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "version",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("test_case_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("preconditions", sa.Text(), nullable=True),
        sa.Column("steps", sa.JSON(), nullable=True),
        sa.Column("expected_result", sa.Text(), nullable=True),
        sa.Column(
            "priority",
            postgresql.ENUM(
                "critical",
                "high",
                "medium",
                "low",
                name="priority",
                create_type=False,
            ),
            server_default="medium",
            nullable=False,
        ),
        sa.Column(
            "is_automated",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["test_case_id"],
            ["test_cases.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_test_case_versions_test_case_id",
        "test_case_versions",
        ["test_case_id"],
    )
    op.create_index(
        "ix_test_case_versions_version_number",
        "test_case_versions",
        ["test_case_id", "version_number"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_test_case_versions_version_number",
        table_name="test_case_versions",
    )
    op.drop_index(
        "ix_test_case_versions_test_case_id",
        table_name="test_case_versions",
    )
    op.drop_table("test_case_versions")
    op.drop_index("ix_test_cases_status", table_name="test_cases")
    op.drop_column("test_cases", "rejection_reason")
    op.drop_column("test_cases", "status")

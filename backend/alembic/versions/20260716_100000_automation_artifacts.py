"""automation_artifacts table

Revision ID: pw_gen_001
Revises: bdd_gen_001
Create Date: 2026-07-16 10:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "pw_gen_001"
down_revision: Union[str, None] = "bdd_gen_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "automation_artifacts",
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
        sa.Column("story_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "language",
            sa.String(length=50),
            server_default="typescript",
            nullable=False,
        ),
        sa.Column(
            "framework",
            sa.String(length=50),
            server_default="playwright",
            nullable=False,
        ),
        sa.Column("page_objects", sa.JSON(), nullable=True),
        sa.Column("locators", sa.JSON(), nullable=True),
        sa.Column("fixtures", sa.JSON(), nullable=True),
        sa.Column("utilities", sa.JSON(), nullable=True),
        sa.Column("assertions", sa.JSON(), nullable=True),
        sa.Column("hooks", sa.JSON(), nullable=True),
        sa.Column("specs", sa.JSON(), nullable=True),
        sa.Column("source_bdd_feature_ids", sa.JSON(), nullable=True),
        sa.Column("source_test_case_ids", sa.JSON(), nullable=True),
        sa.Column(
            "use_bdd",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "use_test_cases",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "include_drafts",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("raw_response", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_automation_artifacts_story_id",
        "automation_artifacts",
        ["story_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_automation_artifacts_story_id",
        table_name="automation_artifacts",
    )
    op.drop_table("automation_artifacts")

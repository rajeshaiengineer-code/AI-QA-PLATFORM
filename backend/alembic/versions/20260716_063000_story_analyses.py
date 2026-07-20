"""story analyses table

Revision ID: story_analysis_001
Revises: workflow_001
Create Date: 2026-07-16 06:30:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "story_analysis_001"
down_revision: Union[str, None] = "workflow_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "story_analyses",
        sa.Column("story_id", sa.Uuid(), nullable=False),
        sa.Column(
            "complexity",
            sa.String(length=20),
            server_default="medium",
            nullable=False,
        ),
        sa.Column(
            "risk",
            sa.String(length=20),
            server_default="medium",
            nullable=False,
        ),
        sa.Column(
            "automation_candidate",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("dependencies", sa.JSON(), nullable=True),
        sa.Column("suggested_tests", sa.JSON(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("model", sa.String(length=100), nullable=True),
        sa.Column("raw_response", sa.JSON(), nullable=True),
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
        sa.ForeignKeyConstraint(["story_id"], ["stories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_story_analyses_story_id", "story_analyses", ["story_id"])
    op.create_index("ix_story_analyses_is_deleted", "story_analyses", ["is_deleted"])


def downgrade() -> None:
    op.drop_index("ix_story_analyses_is_deleted", table_name="story_analyses")
    op.drop_index("ix_story_analyses_story_id", table_name="story_analyses")
    op.drop_table("story_analyses")

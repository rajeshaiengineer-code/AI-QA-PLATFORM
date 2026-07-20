"""failure_analyses table + bugs metadata / failure_analysis_id

Revision ID: fail_bug_001
Revises: pw_gen_001
Create Date: 2026-07-16 11:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "fail_bug_001"
down_revision: Union[str, None] = "pw_gen_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "failure_analyses",
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column(
            "category",
            sa.String(length=40),
            server_default="unknown",
            nullable=False,
        ),
        sa.Column(
            "is_flaky",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column(
            "is_product_bug",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=False),
        sa.Column("suggested_fix", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("logs", sa.Text(), nullable=True),
        sa.Column("screenshot_url", sa.String(length=1000), nullable=True),
        sa.Column("video_url", sa.String(length=1000), nullable=True),
        sa.Column("network_url", sa.String(length=1000), nullable=True),
        sa.Column("trace_url", sa.String(length=1000), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["execution_id"],
            ["executions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_failure_analyses_execution_id",
        "failure_analyses",
        ["execution_id"],
    )
    op.create_index(
        "ix_failure_analyses_category",
        "failure_analyses",
        ["category"],
    )
    op.create_index(
        "ix_failure_analyses_is_deleted",
        "failure_analyses",
        ["is_deleted"],
    )

    op.add_column(
        "bugs",
        sa.Column("failure_analysis_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "bugs",
        sa.Column("extra_metadata", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_bugs_failure_analysis_id",
        "bugs",
        ["failure_analysis_id"],
    )
    op.create_foreign_key(
        "fk_bugs_failure_analysis_id_failure_analyses",
        "bugs",
        "failure_analyses",
        ["failure_analysis_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_bugs_failure_analysis_id_failure_analyses",
        "bugs",
        type_="foreignkey",
    )
    op.drop_index("ix_bugs_failure_analysis_id", table_name="bugs")
    op.drop_column("bugs", "extra_metadata")
    op.drop_column("bugs", "failure_analysis_id")

    op.drop_index("ix_failure_analyses_is_deleted", table_name="failure_analyses")
    op.drop_index("ix_failure_analyses_category", table_name="failure_analyses")
    op.drop_index("ix_failure_analyses_execution_id", table_name="failure_analyses")
    op.drop_table("failure_analyses")

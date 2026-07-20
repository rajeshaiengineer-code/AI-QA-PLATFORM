"""test case category source tags

Revision ID: test_case_gen_001
Revises: story_analysis_001
Create Date: 2026-07-16 07:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "test_case_gen_001"
down_revision: Union[str, None] = "story_analysis_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "test_cases",
        sa.Column("category", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "test_cases",
        sa.Column(
            "source",
            sa.String(length=50),
            server_default="manual",
            nullable=False,
        ),
    )
    op.add_column(
        "test_cases",
        sa.Column("tags", sa.JSON(), nullable=True),
    )
    op.add_column(
        "test_cases",
        sa.Column("provider", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "test_cases",
        sa.Column("model", sa.String(length=100), nullable=True),
    )
    op.create_index("ix_test_cases_category", "test_cases", ["category"])
    op.create_index("ix_test_cases_source", "test_cases", ["source"])


def downgrade() -> None:
    op.drop_index("ix_test_cases_source", table_name="test_cases")
    op.drop_index("ix_test_cases_category", table_name="test_cases")
    op.drop_column("test_cases", "model")
    op.drop_column("test_cases", "provider")
    op.drop_column("test_cases", "tags")
    op.drop_column("test_cases", "source")
    op.drop_column("test_cases", "category")

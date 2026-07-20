"""
Reusable SQLAlchemy column types for domain enums.

Defining Enum types once avoids duplicate PostgreSQL ENUM creation
when the same Python enum is used on multiple tables.
"""

from sqlalchemy import Enum as SAEnum

from app.models.enums import (
    AutomationStatus,
    BugStatus,
    ExecutionStatus,
    Priority,
    StoryStatus,
    StoryType,
)


def _values(enum_cls: type) -> list[str]:
    return [member.value for member in enum_cls]


story_status_enum = SAEnum(
    StoryStatus,
    name="story_status",
    values_callable=_values,
    native_enum=True,
)

story_type_enum = SAEnum(
    StoryType,
    name="story_type",
    values_callable=_values,
    native_enum=True,
)

priority_enum = SAEnum(
    Priority,
    name="priority",
    values_callable=_values,
    native_enum=True,
)

automation_status_enum = SAEnum(
    AutomationStatus,
    name="automation_status",
    values_callable=_values,
    native_enum=True,
)

execution_status_enum = SAEnum(
    ExecutionStatus,
    name="execution_status",
    values_callable=_values,
    native_enum=True,
)

bug_status_enum = SAEnum(
    BugStatus,
    name="bug_status",
    values_callable=_values,
    native_enum=True,
)

__all__ = [
    "SITE_ID_LEN",
    "create_message_table",
    "create_jira_fields_table",
]

import uuid

import sqlalchemy as sa
import sqlalchemy.types as saty
from sqlalchemy.dialects.postgresql import UUID

# Length of the site_id field.
SITE_ID_LEN = 16

# Length of the category field.
CATEGORY_LEN = 50

# Length of the time_lost_type field.
TIME_LOST_TYPE_LEN = 50


def create_message_table(metadata: sa.MetaData) -> sa.Table:
    """Make a model of the narrativelog message table.

    Parameters
    ----------
    metadata: sa.MetaData
        SQLAlchemy metadata object.

    Returns
    -------
    table: sa.Table
        SQLAlchemy table object for message.
    """
    table = sa.Table(
        "message",
        metadata,
        # See https://stackoverflow.com/a/49398042 for UUID:
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
        ),
        sa.Column("site_id", saty.String(length=SITE_ID_LEN)),
        sa.Column("message_text", saty.Text(), nullable=False),
        sa.Column("level", saty.Integer(), nullable=False),
        sa.Column("tags", saty.ARRAY(sa.Text), nullable=False),
        sa.Column("urls", saty.ARRAY(sa.Text), nullable=False),
        sa.Column("time_lost", saty.Interval(), nullable=False),
        sa.Column("date_begin", saty.DateTime(), nullable=True),
        sa.Column("user_id", saty.String(), nullable=False),
        sa.Column("user_agent", saty.String(), nullable=False),
        sa.Column("is_human", saty.Boolean(), nullable=False),
        sa.Column(
            "is_valid",
            saty.Boolean(),
            sa.Computed("date_invalidated is null"),
            nullable=False,
        ),
        sa.Column("date_added", saty.DateTime(), nullable=False),
        sa.Column("date_invalidated", saty.DateTime(), nullable=True),
        sa.Column("parent_id", UUID(as_uuid=True), nullable=True),
        # Added 2022-07-19
        sa.Column("systems", saty.ARRAY(sa.Text), nullable=True),
        sa.Column("subsystems", saty.ARRAY(sa.Text), nullable=True),
        sa.Column("cscs", saty.ARRAY(sa.Text), nullable=True),
        # Added 2022-07-37
        sa.Column("date_end", saty.DateTime(), nullable=True),
        # Added 2023-10-24
        sa.Column("category", saty.String(length=CATEGORY_LEN), nullable=True),
        sa.Column(
            "time_lost_type",
            saty.String(length=TIME_LOST_TYPE_LEN),
            nullable=True,
        ),
        # Constraints
        sa.ForeignKeyConstraint(["parent_id"], ["message.id"]),
    )

    for name in (
        "level",
        "tags",
        "time_lost",
        "user_id",
        "is_valid",
        "date_added",
        "category",
        "time_lost_type",
    ):
        sa.Index(f"idx_{name}", table.columns[name])

    return table


def create_jira_fields_table(metadata: sa.MetaData) -> sa.Table:
    """Make a model of the narrativelog jira fields table.

    Parameters
    ----------
    metadata: sa.MetaData
        SQLAlchemy metadata object.

    Returns
    -------
    table: sa.Table
        SQLAlchemy table object for jira_fields.
    """
    table = sa.Table(
        "jira_fields",
        metadata,
        sa.Column(
            "id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
        ),
        sa.Column("components", saty.ARRAY(sa.Text), nullable=True),
        sa.Column(
            "primary_software_components", saty.ARRAY(sa.Text), nullable=True
        ),
        sa.Column(
            "primary_hardware_components", saty.ARRAY(sa.Text), nullable=True
        ),
        sa.Column("message_id", UUID(as_uuid=True), nullable=False),
        # Constraints
        sa.ForeignKeyConstraint(["message_id"], ["message.id"]),
    )

    return table

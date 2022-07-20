__all__ = ["SITE_ID_LEN", "create_message_table"]

import uuid

import sqlalchemy as sa
import sqlalchemy.types as saty
from sqlalchemy.dialects.postgresql import UUID

# Length of the site_id field.
SITE_ID_LEN = 16


def create_message_table() -> sa.Table:
    """Make a model of the narrativelog message table."""
    table = sa.Table(
        "message",
        sa.MetaData(),
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
        sa.Column("date_user_specified", saty.DateTime(), nullable=True),
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
        sa.Column("systems", saty.ARRAY(sa.Text), nullable=False),
        sa.Column("subsystems", saty.ARRAY(sa.Text), nullable=False),
        sa.Column("cscs", saty.ARRAY(sa.Text), nullable=False),
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
    ):
        sa.Index(f"idx_{name}", table.columns[name])

    return table

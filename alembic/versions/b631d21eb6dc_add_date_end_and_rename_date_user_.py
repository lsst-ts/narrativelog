"""add date_end and rename date_user_specified to date_begin

Revision ID: b631d21eb6dc
Revises: c5780561f83b
Create Date: 2022-07-27 10:21:20.598038

"""
import logging

import sqlalchemy as sa
import sqlalchemy.types as saty

from alembic import op

# revision identifiers, used by Alembic.
revision = "b631d21eb6dc"
down_revision = "c5780561f83b"
branch_labels = None
depends_on = None


MESSAGE_TABLE_NAME = "message"


def upgrade(log: logging.Logger, table_names: set[str]) -> None:
    if MESSAGE_TABLE_NAME not in table_names:
        log.info(f"No {MESSAGE_TABLE_NAME} table; nothing to do")
        return
    log.info(
        "Rename 'date_begin' column to 'date_user_specified' and "
        "add 'date_end' column"
    )
    op.alter_column(
        table_name=MESSAGE_TABLE_NAME,
        column_name="date_user_specified",
        new_column_name="date_begin",
    )
    op.add_column(
        table_name=MESSAGE_TABLE_NAME,
        column=sa.Column("date_end", saty.DateTime(), nullable=True),
    )


def downgrade(log: logging.Logger, table_names: set[str]) -> None:
    if MESSAGE_TABLE_NAME not in table_names:
        log.info(f"No {MESSAGE_TABLE_NAME} table; nothing to do")
        return

    log.info(
        "Rename 'date_user_specified' column to 'date_begin' and "
        "drop 'date_end' column"
    )
    op.alter_column(
        table_name=MESSAGE_TABLE_NAME,
        column_name="date_begin",
        new_column_name="date_user_specified",
    )
    op.drop_column(table_name=MESSAGE_TABLE_NAME, column_name="date_end")

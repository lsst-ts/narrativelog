"""add category and time_lost_type parameters

Revision ID: 54f755dbdb6f
Revises: d9606992ad8d
Create Date: 2023-10-24 14:19:37.665359

"""
import logging

import sqlalchemy as sa
import sqlalchemy.types as saty

from alembic import op

# revision identifiers, used by Alembic.
revision = "54f755dbdb6f"
down_revision = "d9606992ad8d"
branch_labels = None
depends_on = None


MESSAGE_TABLE_NAME = "message"
CATEGORY_LEN = 50
TIME_LOST_TYPE_LEN = 50


def upgrade(log: logging.Logger, table_names: set[str]) -> None:
    if MESSAGE_TABLE_NAME not in table_names:
        log.info(f"No {MESSAGE_TABLE_NAME} table; nothing to do")
        return
    log.info("Add 'category' column and add 'time_lost_type' column")
    op.add_column(
        table_name=MESSAGE_TABLE_NAME,
        column=sa.Column(
            "category", saty.String(length=CATEGORY_LEN), nullable=True
        ),
    )
    op.add_column(
        table_name=MESSAGE_TABLE_NAME,
        column=sa.Column(
            "time_lost_type",
            saty.String(length=TIME_LOST_TYPE_LEN),
            nullable=True,
        ),
    )


def downgrade(log: logging.Logger, table_names: set[str]) -> None:
    if MESSAGE_TABLE_NAME not in table_names:
        log.info(f"No {MESSAGE_TABLE_NAME} table; nothing to do")
        return

    log.info("Drop 'category' column and drop 'time_lost_type' column")
    op.drop_column(table_name=MESSAGE_TABLE_NAME, column_name="category")
    op.drop_column(table_name=MESSAGE_TABLE_NAME, column_name="time_lost_type")

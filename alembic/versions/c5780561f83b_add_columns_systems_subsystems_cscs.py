"""add columns 'systems', 'subsystems', and 'cscs'

Revision ID: c5780561f83b
Revises: 3bb3cd14b2dd
Create Date: 2022-07-19 16:00:51.400669
"""
import logging

import sqlalchemy as sa
import sqlalchemy.types as saty

from alembic import op

# revision identifiers, used by Alembic.
revision = "c5780561f83b"
down_revision = "3bb3cd14b2dd"
branch_labels = None
depends_on = None

MESSAGE_TABLE_NAME = "message"


def upgrade(log: logging.Logger, table_names: set[str]) -> None:
    if MESSAGE_TABLE_NAME not in table_names:
        log.info(f"No {MESSAGE_TABLE_NAME} table; nothing to do")
        return
    log.info("Add columns 'systems', 'subsystems', and 'cscs'")
    op.add_column(
        MESSAGE_TABLE_NAME,
        sa.Column("systems", saty.ARRAY(sa.Text), nullable=True),
    )
    op.add_column(
        MESSAGE_TABLE_NAME,
        sa.Column("subsystems", saty.ARRAY(sa.Text), nullable=True),
    )
    op.add_column(
        MESSAGE_TABLE_NAME,
        sa.Column("cscs", saty.ARRAY(sa.Text), nullable=True),
    )
    # "{ }" is Postgres syntax for an empty list
    op.execute(f"UPDATE {MESSAGE_TABLE_NAME} SET systems = '{{ }}'")
    op.execute(f"UPDATE {MESSAGE_TABLE_NAME} SET subsystems = '{{ }}'")
    op.execute(f"UPDATE {MESSAGE_TABLE_NAME} SET cscs = '{{ }}'")
    op.alter_column(MESSAGE_TABLE_NAME, "systems", nullable=False)
    op.alter_column(MESSAGE_TABLE_NAME, "subsystems", nullable=False)
    op.alter_column(MESSAGE_TABLE_NAME, "cscs", nullable=False)


def downgrade(log: logging.Logger, table_names: set[str]) -> None:
    if MESSAGE_TABLE_NAME not in table_names:
        log.info(f"No {MESSAGE_TABLE_NAME} table; nothing to do")
        return

    log.info("Drop columns 'systems', 'subsystems', and 'cscs'")
    op.drop_column(MESSAGE_TABLE_NAME, "systems")
    op.drop_column(MESSAGE_TABLE_NAME, "subsystems")
    op.drop_column(MESSAGE_TABLE_NAME, "cscs")

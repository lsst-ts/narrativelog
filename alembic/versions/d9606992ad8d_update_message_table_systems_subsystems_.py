"""update message table systems, subsystems and cscs fields

Revision ID: d9606992ad8d
Revises: b631d21eb6dc
Create Date: 2023-09-11 17:44:07.705399

"""
import logging

from alembic import op

# revision identifiers, used by Alembic.
revision = "d9606992ad8d"
down_revision = "b631d21eb6dc"
branch_labels = None
depends_on = None

MESSAGE_TABLE_NAME = "message"


def upgrade(log: logging.Logger, table_names: set[str]):
    if MESSAGE_TABLE_NAME not in table_names:
        log.info(f"No {MESSAGE_TABLE_NAME} table; nothing to do")
        return
    log.info("Set columns 'systems', 'subsystems', and 'cscs' as nullable")

    op.alter_column(MESSAGE_TABLE_NAME, "systems", nullable=True)
    op.alter_column(MESSAGE_TABLE_NAME, "subsystems", nullable=True)
    op.alter_column(MESSAGE_TABLE_NAME, "cscs", nullable=True)


def downgrade(log: logging.Logger, table_names: set[str]):
    if MESSAGE_TABLE_NAME not in table_names:
        log.info(f"No {MESSAGE_TABLE_NAME} table; nothing to do")
        return

    log.info("Set columns 'systems', 'subsystems', and 'cscs' as not nullable")
    op.alter_column(MESSAGE_TABLE_NAME, "systems", nullable=False)
    op.alter_column(MESSAGE_TABLE_NAME, "subsystems", nullable=False)
    op.alter_column(MESSAGE_TABLE_NAME, "cscs", nullable=False)

"""add components_json field to jira_fields table

Revision ID: 49ef39173f83
Revises: 54f755dbdb6f
Create Date: 2024-12-18 17:01:39.676895

"""
import logging

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "49ef39173f83"
down_revision = "54f755dbdb6f"
branch_labels = None
depends_on = None


JIRA_FIELDS_TABLE_NAME = "jira_fields"


def upgrade(log: logging.Logger, table_names: set[str]) -> None:
    if JIRA_FIELDS_TABLE_NAME not in table_names:
        log.info(f"No {JIRA_FIELDS_TABLE_NAME} table; nothing to do")
        return
    log.info("Add 'components_json'")

    op.add_column(
        JIRA_FIELDS_TABLE_NAME,
        sa.Column("components_json", sa.JSON(), nullable=True),
    )


def downgrade(log: logging.Logger, table_names: set[str]) -> None:
    if JIRA_FIELDS_TABLE_NAME not in table_names:
        log.info(f"No {JIRA_FIELDS_TABLE_NAME} table; nothing to do")
        return

    log.info("Drop 'components_json'")
    op.drop_column(JIRA_FIELDS_TABLE_NAME, "components_json")

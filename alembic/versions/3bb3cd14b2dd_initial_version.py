"""initial version (no-op)

Revision ID: 3bb3cd14b2dd
Revises:
Create Date: 2022-03-18 16:41:17.505723
"""
import logging

# revision identifiers, used by Alembic.
revision = "3bb3cd14b2dd"
down_revision = None
branch_labels = None
depends_on = None


def upgrade(log: logging.Logger, table_names: set[str]) -> None:
    pass


def downgrade(log: logging.Logger, table_names: set[str]) -> None:
    pass

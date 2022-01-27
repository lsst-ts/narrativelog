from __future__ import annotations

"""Configuration definition."""

__all__ = ["LogMessageDatabase"]

import asyncio

import sqlalchemy.engine
import structlog
from sqlalchemy.ext.asyncio import create_async_engine

from narrativelog.create_message_table import create_message_table


class LogMessageDatabase:
    """Connection to the narrative log database and message table.

    Create the table if it does not exist.

    Parameters
    ----------
    url
        URL of narrative log database server in the form:
        postgresql://[user[:password]@][netloc][:port][/dbname]
    """

    def __init__(self, url: str):
        self._closed = False
        self.url = url
        self.logger = structlog.get_logger("LogMessageDatabase")
        sa_url = sqlalchemy.engine.make_url(url)
        sa_url = sa_url.set(drivername="postgresql+asyncpg")
        self.engine = create_async_engine(sa_url, future=True)
        self.table = create_message_table()
        self.start_task = asyncio.create_task(self.start())

    async def start(self) -> None:
        """Create the table in the database."""
        self.logger.info("Create table")
        async with self.engine.begin() as connection:
            await connection.run_sync(self.table.metadata.create_all)

    async def close(self) -> None:
        """Close the database engine and all connections."""
        if self._closed:
            return
        self._closed = True
        self.start_task.cancel()
        await self.engine.dispose()

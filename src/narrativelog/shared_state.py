from __future__ import annotations

__all__ = ["create_shared_state", "delete_shared_state", "get_shared_state"]

import logging
import os
import typing
import urllib

from .create_message_table import SITE_ID_LEN, create_message_table
from .log_message_database import LogMessageDatabase

_shared_state: typing.Optional[SharedState] = None


def get_env(name: str, default: typing.Optional[str] = None) -> str:
    """Get a value from an environment variable.

    Parameters
    ----------
    name
        The name of the environment variable.
    default
        The default value; if None then raise ValueError if absent.
    """
    if default is not None and not isinstance(default, str):
        raise ValueError(f"default={default!r} must be a str or None")
    value = os.environ.get(name, default)
    if value is None:
        raise ValueError(f"You must specify environment variable {name}")
    return value


def create_db_url() -> str:
    """Create the narrativelog database URL from environment variables."""
    narrativelog_db_user = get_env("NARRATIVELOG_DB_USER", "narrativelog")
    narrativelog_db_password = get_env("NARRATIVELOG_DB_PASSWORD", "")
    narrativelog_db_host = get_env("NARRATIVELOG_DB_HOST", "localhost")
    narrativelog_db_port = int(get_env("NARRATIVELOG_DB_PORT", "5432"))
    narrativelog_db_database = get_env(
        "NARRATIVELOG_DB_DATABASE", "narrativelog"
    )
    encoded_db_password = urllib.parse.quote_plus(narrativelog_db_password)
    return (
        f"postgresql+asyncpg://{narrativelog_db_user}:{encoded_db_password}"
        f"@{narrativelog_db_host}:{narrativelog_db_port}"
        f"/{narrativelog_db_database}"
    )


class SharedState:
    """Shared application state.

    All attributes are set by environment variables.

    Attributes
    ----------
    narrativelog_db : sa.Table
    site_id : str
        Name identifying where the narrativelog service is running.
        Values include: "summit" and "base".

    Notes
    -----
    Reads the following env variables:

    narrativelog_db_user
        Narrative log database user name.
    narrativelog_db_password
        Narrative log database password.
    narrativelog_db_host
        Narrative log database TCP/IP host.
    narrativelog_db_port
        Narrative log database TCP/IP port.
    narrativelog_db_database
        Name of narrativelog database.
    site_id
        String identifying where the narrativelog service is running.
        Values include: "summit" and "base".
    """

    def __init__(self):  # type: ignore
        self.site_id = get_env("SITE_ID")
        if len(self.site_id) > SITE_ID_LEN:
            raise ValueError(
                f"SITE_ID={self.site_id!r} too long; max length={SITE_ID_LEN}"
            )
        self.log = logging.getLogger("narrativelog")

        self.narrativelog_db = LogMessageDatabase(
            message_table=create_message_table(), url=create_db_url()
        )


async def create_shared_state() -> None:
    """Create, start and then set the application shared state.

    Raises
    ------
    RuntimeError
            If the shared state has already been created.
    """
    global _shared_state
    if _shared_state is not None:
        raise RuntimeError("Shared state already created")
    state = SharedState()
    await state.narrativelog_db.start_task
    _shared_state = state


async def delete_shared_state() -> None:
    """Delete and then close the application shared state."""
    global _shared_state
    if _shared_state is None:
        return
    state = _shared_state
    _shared_state = None
    await state.narrativelog_db.close()


def get_shared_state() -> SharedState:
    """Get the application shared state.

    Raises
    ------
    RuntimeError
            If the shared state has not been created.
    """
    global _shared_state
    if _shared_state is None:
        raise RuntimeError("Shared state not created")
    return _shared_state


def has_shared_state() -> bool:
    """Has the application shared state been created?"""
    global _shared_state
    return _shared_state is not None

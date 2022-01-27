from __future__ import annotations

__all__ = ["add_message"]

import datetime
import typing

import astropy.time
import fastapi
import sqlalchemy as sa

from ..message import Message
from ..shared_state import SharedState, get_shared_state
from .normalize_tags import TAG_DESCRIPTION, normalize_tags

router = fastapi.APIRouter()


# The pair of decorators avoids a redirect from uvicorn if the trailing "/"
# is not as expected. include_in_schema=False hides one from the API docs.
# https://github.com/tiangolo/fastapi/issues/2060
@router.post("/messages", response_model=Message)
@router.post("/messages/", response_model=Message, include_in_schema=False)
async def add_message(
    message_text: str = fastapi.Body(..., description="Message text"),
    level: int = fastapi.Body(
        ..., description="Message level; a python logging level."
    ),
    tags: typing.List[str] = fastapi.Body(
        default=[],
        description="Tags describing the message, as space-separated words. "
        + TAG_DESCRIPTION,
    ),
    urls: typing.List[str] = fastapi.Body(
        default=[],
        description="URLs of associated JIRA tickets, screen shots, etc.: "
        "space-separated.",
    ),
    time_lost: datetime.timedelta = fastapi.Body(
        default=datetime.timedelta(),
        description="Estimate of lost on-sky time. Defaults to 0.",
    ),
    date_user_specified: typing.Optional[datetime.datetime] = fastapi.Body(
        default=None,
        description="Approximate TAI date at which this message is relevant "
        "(if different than the time at which the message was specified)",
    ),
    user_id: str = fastapi.Body(..., description="User ID"),
    user_agent: str = fastapi.Body(
        default=...,
        description="User agent (name of application creating the message)",
    ),
    is_human: bool = fastapi.Body(
        default=...,
        description="Was the message created by a human being?",
    ),
    state: SharedState = fastapi.Depends(get_shared_state),
) -> Message:
    """Add a message to the database and return the added message."""
    curr_tai = astropy.time.Time.now()

    tags = normalize_tags(tags)

    el_table = state.narrativelog_db.table

    # Add the message.
    async with state.narrativelog_db.engine.begin() as connection:
        result = await connection.execute(
            el_table.insert()
            .values(
                site_id=state.site_id,
                message_text=message_text,
                level=level,
                tags=tags,
                urls=urls,
                time_lost=time_lost,
                date_user_specified=date_user_specified,
                user_id=user_id,
                user_agent=user_agent,
                is_human=is_human,
                date_added=curr_tai.tai.datetime,
            )
            .returning(sa.literal_column("*"))
        )
        result = result.fetchone()

    return Message.from_orm(result)

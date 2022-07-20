__all__ = ["add_message"]

import datetime
import http

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
    tags: list[str] = fastapi.Body(
        default=[],
        description="Tags describing the message. " + TAG_DESCRIPTION,
    ),
    systems: list[str] = fastapi.Body(
        default=[],
        description="Zero or more systems to which the message applies.",
    ),
    subsystems: list[str] = fastapi.Body(
        default=[],
        description="Zero or more subsystems to which the message applies",
    ),
    cscs: list[str] = fastapi.Body(
        default=[],
        description="Zero or more CSCs to which the message applies. "
        "Each entry should be in the form 'name' or 'name:index', "
        "where 'name' is the SAL component name and 'index' is the SAL index.",
    ),
    urls: list[str] = fastapi.Body(
        default=[],
        description="URLs of associated JIRA tickets, screen shots, etc.: "
        "space-separated.",
    ),
    time_lost: datetime.timedelta = fastapi.Body(
        default=datetime.timedelta(),
        description="Estimate of lost on-sky time. Defaults to 0.",
    ),
    date_user_specified: None
    | datetime.datetime = fastapi.Body(
        default=None,
        description="Approximate TAI date at which this message is relevant "
        "(if different than the time at which the message was specified). "
        "Specify as an ISO 8601 string with no time zone suffix (not even Z).",
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

    if date_user_specified and date_user_specified.tzinfo is not None:
        # Note:  I don't know how to make the router accept dates with
        # any time zone other than None (no suffix, good) or UTC
        # (suffix Z, bad because UTC is not TAI).
        # Appending ±hh.mm is rejected before the router runs.
        # But in any case reject all time zones.
        raise fastapi.HTTPException(
            status_code=http.HTTPStatus.BAD_REQUEST,
            detail="date_user_specified must not have a time zone suffix",
        )

    tags = normalize_tags(tags)

    message_table = state.narrativelog_db.message_table

    # Add the message.
    async with state.narrativelog_db.engine.begin() as connection:
        result = await connection.execute(
            message_table.insert()
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
                systems=systems,
                subsystems=subsystems,
                cscs=cscs,
            )
            .returning(sa.literal_column("*"))
        )
        result = result.fetchone()

    return Message.from_orm(result)

from __future__ import annotations

__all__ = ["edit_message"]

import datetime
import http
import typing

import astropy.time
import fastapi
import sqlalchemy as sa

from ..message import Message
from ..shared_state import SharedState, get_shared_state
from .normalize_tags import TAG_DESCRIPTION, normalize_tags

router = fastapi.APIRouter()


@router.patch("/messages/{id}", response_model=Message)
async def edit_message(
    id: str,
    message_text: typing.Optional[str] = fastapi.Body(
        default=None, description="Message text"
    ),
    level: typing.Optional[int] = fastapi.Body(
        default=None,
        description="Message level; a python logging level.",
    ),
    tags: typing.Optional[typing.List[str]] = fastapi.Body(
        default=None,
        description="Tags describing the message, as space-separated words. "
        "If specified, replaces the existing set of tags. " + TAG_DESCRIPTION,
    ),
    urls: typing.Optional[typing.List[str]] = fastapi.Body(
        default=None,
        description="URLs of associated JIRA tickets, screen shots, etc.: "
        "space-separated. If specified, replaces the existing set.",
    ),
    time_lost: typing.Optional[datetime.timedelta] = fastapi.Body(
        default=None, description="Estimate of lost on-sky time."
    ),
    date_user_specified: typing.Optional[datetime.datetime] = fastapi.Body(
        default=None,
        description="Approximate TAI date at which this message is relevant "
        "(if different than the time at which the message was specified)",
    ),
    site_id: typing.Optional[str] = fastapi.Body(
        default=None, description="Site ID"
    ),
    user_id: typing.Optional[str] = fastapi.Body(
        default=None, description="User ID"
    ),
    user_agent: typing.Optional[str] = fastapi.Body(
        default=None,
        description="User agent (which app created the message)",
    ),
    is_human: typing.Optional[bool] = fastapi.Body(
        default=None,
        description="Was the message created by a human being?",
    ),
    state: SharedState = fastapi.Depends(get_shared_state),
) -> Message:
    """Edit an existing message.

    The process is:

    - Read the message to edit; call this the parent message.
    - Create a new message using the parent message data,
      overridden by the new user-supplied data.
      Set parent_id of the new message to the id of the parent message,
      in order to provide a link to the parent message.
    - Set timestamp_is_valid_changed=now on the parent message.
    """
    el_table = state.narrativelog_db.table

    parent_id = id
    old_site_id = site_id

    if tags is not None:
        tags = normalize_tags(tags)

    request_data = dict(id=id, site_id=site_id)
    for name in (
        "message_text",
        "level",
        "tags",
        "urls",
        "time_lost",
        "date_user_specified",
        "site_id",
        "user_id",
        "user_agent",
        "is_human",
    ):

        value = locals()[name]
        if value is not None:
            request_data[name] = value

    async with state.narrativelog_db.engine.begin() as connection:
        # Find the parent message.
        get_parent_result = await connection.execute(
            el_table.select()
            .where(el_table.c.id == parent_id)
            .with_for_update()
        )
        parent_row = get_parent_result.fetchone()
        if parent_row is None:
            raise fastapi.HTTPException(
                status_code=http.HTTPStatus.NOT_FOUND,
                detail=f"Message with id={parent_id} not found",
            )

        # Add and get the new message.
        new_data = dict(parent_row._mapping).copy()
        new_data.update(request_data)
        for field in ("id", "is_valid", "date_invalidated"):
            del new_data[field]
        current_tai = astropy.time.Time.now().tai.datetime
        new_data["site_id"] = state.site_id
        new_data["date_added"] = current_tai
        new_data["parent_id"] = parent_id
        add_row = await connection.execute(
            el_table.insert()
            .values(**new_data)
            .returning(sa.literal_column("*"))
        )
        add_row = add_row.fetchone()

        # Mark the parent message as invalid.
        await connection.execute(
            el_table.update()
            .where(el_table.c.id == parent_id)
            .values(date_invalidated=current_tai)
        )

    return Message.from_orm(add_row)

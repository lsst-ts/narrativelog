from __future__ import annotations

__all__ = ["find_messages"]

import datetime
import enum
import typing

import fastapi
import sqlalchemy as sa

from ..message import Message
from ..shared_state import SharedState, get_shared_state
from .normalize_tags import TAG_DESCRIPTION, normalize_tags

router = fastapi.APIRouter()


class TriState(str, enum.Enum):
    either = "either"
    true = "true"
    false = "false"


@router.get("/messages", response_model=typing.List[Message])
@router.get(
    "/messages/", response_model=typing.List[Message], include_in_schema=False
)
async def find_messages(
    site_ids: typing.Optional[typing.List[str]] = fastapi.Query(
        default=None,
        description="Site IDs.",
    ),
    message_text: typing.Optional[str] = fastapi.Query(
        default=None,
        description="Message text contains...",
    ),
    min_level: typing.Optional[int] = fastapi.Query(
        default=None, description="Minimum level, inclusive."
    ),
    max_level: typing.Optional[int] = fastapi.Query(
        default=None, description="Maximum level, exclusive."
    ),
    user_ids: typing.Optional[typing.List[str]] = fastapi.Query(
        default=None,
        description="User IDs. Repeat the parameter for each value.",
    ),
    user_agents: typing.Optional[typing.List[str]] = fastapi.Query(
        default=None,
        description="User agents (which app created the message). "
        "Repeat the parameter for each value.",
    ),
    tags: typing.Optional[typing.List[str]] = fastapi.Query(
        default=None,
        description="Tags, at least one of which must be present. "
        + TAG_DESCRIPTION,
    ),
    exclude_tags: typing.Optional[typing.List[str]] = fastapi.Query(
        default=None,
        description="Tags, all of which must be absent. " + TAG_DESCRIPTION,
    ),
    urls: typing.Optional[typing.List[str]] = fastapi.Query(
        default=None,
        desription="URLs, or fragments of URLs, "
        "at least one of which must be present.",
    ),
    min_time_lost: typing.Optional[datetime.timedelta] = fastapi.Query(
        default=None, description="Minimum time lost."
    ),
    max_time_lost: typing.Optional[datetime.timedelta] = fastapi.Query(
        default=None, description="Maximum time lost."
    ),
    has_date_user_specified: typing.Optional[bool] = fastapi.Query(
        default=None,
        description="Does this message have a non-null date_user_specified?",
    ),
    min_date_user_specified: typing.Optional[
        datetime.datetime
    ] = fastapi.Query(
        default=None, description="Minimum user-specified TAI date."
    ),
    max_date_user_specified: typing.Optional[
        datetime.datetime
    ] = fastapi.Query(
        default=None, description="Maximum user-specified TAI date."
    ),
    is_human: TriState = fastapi.Query(
        default=TriState.either,
        description="Was the message created by a human being?",
    ),
    is_valid: TriState = fastapi.Query(
        default=TriState.true,
        description="Is the message valid? (False if deleted or superseded)",
    ),
    min_date_added: typing.Optional[datetime.datetime] = fastapi.Query(
        default=None,
        description="Minimum date the message was added, inclusive; "
        "TAI as an ISO string with no timezone information",
    ),
    max_date_added: typing.Optional[datetime.datetime] = fastapi.Query(
        default=None,
        description="Maximum date the message was added, exclusive; "
        "TAI as an ISO string with no timezone information",
    ),
    has_date_invalidated: typing.Optional[bool] = fastapi.Query(
        default=None,
        description="Does this message have a non-null date_invalidated?",
    ),
    min_date_invalidated: typing.Optional[datetime.datetime] = fastapi.Query(
        default=None,
        description="Minimum date the is_valid flag was last toggled, inclusive, "
        "TAI as an ISO string with no timezone information",
    ),
    max_date_invalidated: typing.Optional[datetime.datetime] = fastapi.Query(
        default=None,
        description="Maximum date the is_valid flag was last toggled, exclusive, "
        "TAI as an ISO string with no timezone information",
    ),
    has_parent_id: typing.Optional[bool] = fastapi.Query(
        default=None,
        description="Does this message have a non-null parent ID?",
    ),
    order_by: typing.List[str] = fastapi.Query(
        default=["date_added"],
        description="Fields to sort by. "
        "Prefix a name with - for descending order, e.g. -id. "
        "Repeat the parameter for each value.",
    ),
    offset: int = fastapi.Query(
        default=0,
        description="The number of messages to skip.",
        ge=0,
    ),
    limit: int = fastapi.Query(
        default=50,
        description="The maximum number of number of messages to return.",
        gt=1,
    ),
    state: SharedState = fastapi.Depends(get_shared_state),
) -> list[Message]:
    """Find messages."""
    el_table = state.narrativelog_db.table

    # Names of selection arguments
    select_arg_names = (
        "site_ids",
        "message_text",
        "min_level",
        "max_level",
        "user_ids",
        "user_agents",
        "tags",
        "exclude_tags",
        "urls",
        "min_time_lost",
        "max_time_lost",
        "has_date_user_specified",
        "min_date_user_specified",
        "max_date_user_specified",
        "is_human",
        "is_valid",
        "min_date_added",
        "max_date_added",
        "has_date_invalidated",
        "min_date_invalidated",
        "max_date_invalidated",
        "has_parent_id",
        "order_by",
    )

    if tags is not None:
        tags = normalize_tags(tags)
    if exclude_tags is not None:
        exclude_tags = normalize_tags(exclude_tags)

    async with state.narrativelog_db.engine.connect() as connection:
        conditions = []
        order_by_columns = []
        order_by_id = False
        # Handle minimums and maximums
        for key in select_arg_names:
            value = locals()[key]
            if value is None:
                continue
            if key.startswith("min_"):
                column = el_table.columns[key[4:]]
                conditions.append(column >= value)
            elif key.startswith("max_"):
                column = el_table.columns[key[4:]]
                conditions.append(column < value)
            elif key.startswith("has_"):
                column = el_table.columns[key[4:]]
                if value:
                    conditions.append(column != None)  # noqa
                else:
                    conditions.append(column == None)  # noqa
            elif key in (
                "tags",
                "urls",
            ):
                # Field is an array and value is a list. Field name is the key.
                # Return messages for which any item in the array matches
                # matches any item in "value" (PostgreSQL's && operator).
                # Notes:
                # * The list cannot be empty, because the array is passed
                #   by listing the parameter once per value.
                # * The postgres-specific ARRAY field has an "overlap"
                #   method that does the same thing as the && operator,
                #   but the generic ARRAY field does not have this method.
                #   The generic ARRAY field is easier to work with,
                #   because it handles list directly, whereas the
                #   postgres-specific ARRAY field requires casting lists.
                column = el_table.columns[key]
                conditions.append(column.op("&&")(value))
            elif key == "exclude_tags":
                # Value is a list; field name is the key.
                # Note: the list cannot be empty, because the array is passed
                # by listing the parameter once per value.
                column = el_table.columns["tags"]
                conditions.append(sa.sql.not_(column.op("&&")(value)))
            elif key in (
                "site_ids",
                "instruments",
                "user_ids",
                "user_agents",
            ):
                # Value is a list; field name is key without the final "s".
                # Note: the list cannot be empty, because the array is passed
                # by listing the parameter once per value.
                column = el_table.columns[key[:-1]]
                conditions.append(column.in_(value))
            elif key in ("message_text",):
                column = el_table.columns[key]
                conditions.append(column.contains(value))
            elif key in ("is_human", "is_valid"):
                if value != TriState.either:
                    logical_value = value == TriState.true
                    column = el_table.columns[key]
                    conditions.append(column == logical_value)
            elif key == "order_by":
                for item in value:
                    if item.startswith("-"):
                        column_name = item[1:]
                        column = el_table.columns[column_name]
                        order_by_columns.append(sa.sql.desc(column))
                    else:
                        column_name = item
                        column = el_table.columns[column_name]
                        order_by_columns.append(sa.sql.asc(column))
                    if column_name == "id":
                        order_by_id = True

            else:
                raise RuntimeError(f"Bug: unrecognized key: {key}")

        # If order_by does not include "id" then append it, to make the order
        # repeatable. Otherwise different calls can return data in different
        # orders, which is a disaster when using limit and offset.
        if not order_by_id:
            order_by_columns.append(sa.sql.asc(el_table.c.id))
        if conditions:
            full_conditions = sa.sql.and_(*conditions)
        else:
            full_conditions = sa.sql.and_(True)
        result = await connection.execute(
            el_table.select()
            .where(full_conditions)
            .order_by(*order_by_columns)
            .limit(limit)
            .offset(offset)
        )
        rows = result.fetchall()

    return [Message.from_orm(row) for row in rows]

__all__ = ["find_messages"]

import datetime
import enum
import http

import fastapi
import sqlalchemy as sa

from ..message import MESSAGE_ORDER_BY_VALUES, Message
from ..shared_state import SharedState, get_shared_state
from .normalize_tags import TAG_DESCRIPTION, normalize_tags

router = fastapi.APIRouter()


class TriState(str, enum.Enum):
    either = "either"
    true = "true"
    false = "false"


MESSAGE_ORDER_BY_SET = set(MESSAGE_ORDER_BY_VALUES)


@router.get("/messages", response_model=list[Message])
@router.get(
    "/messages/", response_model=list[Message], include_in_schema=False
)
async def find_messages(
    site_ids: None
    | list[str] = fastapi.Query(
        default=None,
        description="Site IDs.",
    ),
    message_text: None
    | str = fastapi.Query(
        default=None,
        description="Message text contains...",
    ),
    min_level: None
    | int = fastapi.Query(
        default=None, description="Minimum level, inclusive."
    ),
    max_level: None
    | int = fastapi.Query(
        default=None, description="Maximum level, exclusive."
    ),
    user_ids: None
    | list[str] = fastapi.Query(
        default=None,
        description="User IDs. Repeat the parameter for each value.",
    ),
    user_agents: None
    | list[str] = fastapi.Query(
        default=None,
        description="User agents (which app created the message). "
        "Repeat the parameter for each value.",
    ),
    tags: None
    | list[str] = fastapi.Query(
        default=None,
        description="Tags, at least one of which must be present. "
        + TAG_DESCRIPTION,
    ),
    exclude_tags: None
    | list[str] = fastapi.Query(
        default=None,
        description="Tags, all of which must be absent. " + TAG_DESCRIPTION,
    ),
    systems: None
    | list[str] = fastapi.Query(
        default=None,
        description="System names or fragments of names. All messages "
        "with a system that matches any of these are included. "
        "Repeat the parameter for each value.",
    ),
    exclude_systems: None
    | list[str] = fastapi.Query(
        default=None,
        description="System names or fragments of names. All messages "
        "with a system that matches any of these are excluded. "
        "Repeat the parameter for each value.",
    ),
    subsystems: None
    | list[str] = fastapi.Query(
        default=None,
        description="Subsystem names or fragments of names. All messages "
        "with a subsystem that matches any of these are included. "
        "Repeat the parameter for each value.",
    ),
    exclude_subsystems: None
    | list[str] = fastapi.Query(
        default=None,
        description="Subsystem names or fragments of names. All messages "
        "with a subsystem that matches any of these are excluded. "
        "Repeat the parameter for each value.",
    ),
    cscs: None
    | list[str] = fastapi.Query(
        default=None,
        description="CSC names or fragments of CSC names, "
        "of which at least one must be present. "
        "Repeat the parameter for each value.",
    ),
    exclude_cscs: None
    | list[str] = fastapi.Query(
        default=None,
        description="CSC names or fragments of CSC names, "
        "of which all must be absent. "
        "Repeat the parameter for each value.",
    ),
    urls: None
    | list[str] = fastapi.Query(
        default=None,
        desription="URLs, or fragments of URLs, "
        "of which at least one of which must be present. "
        "Repeat the parameter for each value.",
    ),
    min_time_lost: None
    | datetime.timedelta = fastapi.Query(
        default=None, description="Minimum time lost."
    ),
    max_time_lost: None
    | datetime.timedelta = fastapi.Query(
        default=None, description="Maximum time lost."
    ),
    has_date_user_specified: None
    | bool = fastapi.Query(
        default=None,
        description="Does this message have a non-null date_user_specified?",
    ),
    min_date_user_specified: None
    | datetime.datetime = fastapi.Query(
        default=None, description="Minimum user-specified TAI date."
    ),
    max_date_user_specified: None
    | datetime.datetime = fastapi.Query(
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
    min_date_added: None
    | datetime.datetime = fastapi.Query(
        default=None,
        description="Minimum date the message was added, inclusive; "
        "TAI as an ISO string with no timezone information",
    ),
    max_date_added: None
    | datetime.datetime = fastapi.Query(
        default=None,
        description="Maximum date the message was added, exclusive; "
        "TAI as an ISO string with no timezone information",
    ),
    has_date_invalidated: None
    | bool = fastapi.Query(
        default=None,
        description="Does this message have a non-null date_invalidated?",
    ),
    min_date_invalidated: None
    | datetime.datetime = fastapi.Query(
        default=None,
        description="Minimum date the is_valid flag was last toggled, inclusive, "
        "TAI as an ISO string with no timezone information",
    ),
    max_date_invalidated: None
    | datetime.datetime = fastapi.Query(
        default=None,
        description="Maximum date the is_valid flag was last toggled, exclusive, "
        "TAI as an ISO string with no timezone information",
    ),
    has_parent_id: None
    | bool = fastapi.Query(
        default=None,
        description="Does this message have a non-null parent ID?",
    ),
    order_by: None
    | list[str] = fastapi.Query(
        default=None,
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
    message_table = state.narrativelog_db.message_table

    # Names of selection arguments
    select_arg_names = (
        "site_ids",
        "message_text",
        "min_level",
        "max_level",
        "user_ids",
        "user_agents",
        "systems",
        "exclude_systems",
        "subsystems",
        "exclude_subsystems",
        "cscs",
        "exclude_cscs",
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
    )

    # Compute the columns to order by.
    # If order_by does not include "id" then append it, to make the order
    # repeatable. Otherwise different calls can return data in different
    # orders, which is a disaster when using limit and offset.
    order_by_columns = []
    if order_by is None:
        order_by = ["id"]
    else:
        order_by_set = set(order_by)
        bad_fields = order_by_set - MESSAGE_ORDER_BY_SET
        if bad_fields:
            raise fastapi.HTTPException(
                status_code=http.HTTPStatus.BAD_REQUEST,
                detail=f"Invalid order_by fields: {sorted(bad_fields)}; "
                + f"allowed values are {MESSAGE_ORDER_BY_VALUES}",
            )
        if not order_by_set & {"id", "-id"}:
            order_by.append("id")
    for item in order_by:
        if item.startswith("-"):
            column_name = item[1:]
            column = message_table.columns[column_name]
            order_by_columns.append(sa.sql.desc(column))
        else:
            column_name = item
            column = message_table.columns[column_name]
            order_by_columns.append(sa.sql.asc(column))

    if tags is not None:
        tags = normalize_tags(tags)
    if exclude_tags is not None:
        exclude_tags = normalize_tags(exclude_tags)

    async with state.narrativelog_db.engine.connect() as connection:
        conditions = []
        # Handle minimums and maximums
        for key in select_arg_names:
            value = locals()[key]
            if value is None:
                continue
            if key.startswith("min_"):
                column = message_table.columns[key[4:]]
                conditions.append(column >= value)
            elif key.startswith("max_"):
                column = message_table.columns[key[4:]]
                conditions.append(column < value)
            elif key.startswith("has_"):
                column = message_table.columns[key[4:]]
                if value:
                    conditions.append(column != None)  # noqa
                else:
                    conditions.append(column == None)  # noqa
            elif key in {
                "tags",
                "systems",
                "subsystems",
                "cscs",
                "urls",
            }:
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
                column = message_table.columns[key]
                conditions.append(column.op("&&")(value))
            elif key in {
                "exclude_tags",
                "exclude_systems",
                "exclude_subsystems",
                "exclude_cscs",
            }:
                # Value is a list; field name is the end of the key.
                # Note: the list cannot be empty, because the array is passed
                # by listing the parameter once per value.
                column_name = key[8:]
                column = message_table.columns[column_name]
                conditions.append(sa.sql.not_(column.op("&&")(value)))
            elif key in {
                "site_ids",
                "instruments",
                "systems",
                "user_ids",
                "user_agents",
            }:
                # Value is a list; field name is key without the final "s".
                # Note: the list cannot be empty, because the array is passed
                # by listing the parameter once per value.
                column = message_table.columns[key[:-1]]
                conditions.append(column.in_(value))
            elif key in ("message_text",):
                column = message_table.columns[key]
                conditions.append(column.contains(value))
            elif key in {"is_human", "is_valid"}:
                if value != TriState.either:
                    logical_value = value == TriState.true
                    column = message_table.columns[key]
                    conditions.append(column == logical_value)
            else:
                raise RuntimeError(f"Bug: unrecognized key: {key}")

        if conditions:
            full_conditions = sa.sql.and_(*conditions)
        else:
            full_conditions = sa.sql.and_(True)
        result = await connection.execute(
            message_table.select()
            .where(full_conditions)
            .order_by(*order_by_columns)
            .limit(limit)
            .offset(offset)
        )
        rows = result.fetchall()

    return [Message.from_orm(row) for row in rows]

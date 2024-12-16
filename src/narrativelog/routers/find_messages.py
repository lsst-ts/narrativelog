__all__ = ["find_messages"]

import datetime
import enum
import http
import json

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
    categories: None
    | list[str] = fastapi.Query(
        default=None,
        description="Categories, or fragments of categories, "
        "of which at least one must be present. "
        "Repeat the parameter for each value.",
    ),
    exclude_categories: None
    | list[str] = fastapi.Query(
        default=None,
        description="Categories, or fragments of categories, "
        "of which all must be absent. "
        "Repeat the parameter for each value.",
    ),
    time_lost_types: None
    | list[str] = fastapi.Query(
        default=None,
        description="Time lost types, or fragments of time lost types, "
        "of which at least one must be present. "
        "Repeat the parameter for each value.",
    ),
    exclude_time_lost_types: None
    | list[str] = fastapi.Query(
        default=None,
        description="Time lost types, or fragments of time lost types, "
        "of which all must be absent. "
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
        "Repeat the parameter for each value. "
        "**This field is deprecated and will be removed in v1.0.0**. "
        "Please use 'components_path' instead.",
    ),
    exclude_systems: None
    | list[str] = fastapi.Query(
        default=None,
        description="System names or fragments of names. All messages "
        "with a system that matches any of these are excluded. "
        "Repeat the parameter for each value. "
        "**This field is deprecated and will be removed in v1.0.0**. "
        "Please use 'components_path' instead.",
    ),
    subsystems: None
    | list[str] = fastapi.Query(
        default=None,
        description="Subsystem names or fragments of names. All messages "
        "with a subsystem that matches any of these are included. "
        "Repeat the parameter for each value. "
        "**This field is deprecated and will be removed in v1.0.0**. "
        "Please use 'components_path' instead.",
    ),
    exclude_subsystems: None
    | list[str] = fastapi.Query(
        default=None,
        description="Subsystem names or fragments of names. All messages "
        "with a subsystem that matches any of these are excluded. "
        "Repeat the parameter for each value. "
        "**This field is deprecated and will be removed in v1.0.0**. "
        "Please use 'components_path' instead.",
    ),
    cscs: None
    | list[str] = fastapi.Query(
        default=None,
        description="CSC names or fragments of CSC names, "
        "of which at least one must be present. "
        "Repeat the parameter for each value. "
        "**This field is deprecated and will be removed in v1.0.0**. "
        "Please use 'components_path' instead.",
    ),
    exclude_cscs: None
    | list[str] = fastapi.Query(
        default=None,
        description="CSC names or fragments of CSC names, "
        "of which all must be absent. "
        "Repeat the parameter for each value. "
        "**This field is deprecated and will be removed in v1.0.0**. "
        "Please use 'components_path' instead.",
    ),
    components: None
    | list[str] = fastapi.Query(
        default=None,
        description="Component names or fragments of names. All messages "
        "with a component that matches any of these are included. "
        "Repeat the parameter for each value. "
        "Each entry should be a valid component name entry on the OBS jira project. "
        "**This field is deprecated and will be removed in v1.0.0**. "
        "Please use 'components_path' instead.",
    ),
    exclude_components: None
    | list[str] = fastapi.Query(
        default=None,
        description="Component names or fragments of names. All messages "
        "with a component that matches any of these are excluded. "
        "Repeat the parameter for each value. "
        "Each entry should be a valid component name entry on the OBS jira project. "
        "**This field is deprecated and will be removed in v1.0.0**. "
        "Please use 'components_path' instead.",
    ),
    primary_software_components: None
    | list[str] = fastapi.Query(
        default=None,
        description="Primary software components names or fragments of names. "
        "All messages with a component that matches any of these are included. "
        "Repeat the parameter for each value. "
        "Each entry should be a valid component name entry on the OBS jira project. "
        "**This field is deprecated and will be removed in v1.0.0**. "
        "Please use 'components_path' instead.",
    ),
    exclude_primary_software_components: None
    | list[str] = fastapi.Query(
        default=None,
        description="Primary software components names or fragments of names. "
        "All messages with a component that matches any of these are excluded. "
        "Repeat the parameter for each value. "
        "Each entry should be a valid component name entry on the OBS jira project. "
        "**This field is deprecated and will be removed in v1.0.0**. "
        "Please use 'components_path' instead.",
    ),
    primary_hardware_components: None
    | list[str] = fastapi.Query(
        default=None,
        description="Primary hardware components names or fragments of names. "
        "All messages with a component that matches any of these are included. "
        "Repeat the parameter for each value. "
        "Each entry should be a valid component name entry on the OBS jira project. "
        "**This field is deprecated and will be removed in v1.0.0**. "
        "Please use 'components_path' instead.",
    ),
    exclude_primary_hardware_components: None
    | list[str] = fastapi.Query(
        default=None,
        description="Primary hardware components names or fragments of names. "
        "All messages with a component that matches any of these are excluded. "
        "Repeat the parameter for each value. "
        "**This field is deprecated and will be removed in v1.0.0**. "
        "Please use 'components_path' instead.",
    ),
    components_path: None
    | str = fastapi.Query(
        default=None,
        description="Components structure in JSON format to include. "
        'All messages with a "components_json" field that '
        "matches at least a key with any of the values specified within "
        'the "components_path" are included. The JSON object represents the current '
        "hierarchy of systems, subsystems and components on the OBS Jira project: "
        '`{"systems": ["system1", ..., "systemN"], '
        '"subsystems": ["subsystem1", ..., "subsystemN"], '
        '"components": ["component1", ..., "componentN"]}`. '
        'E.g. Setting "components_path" to `{"systems": ["AuxTel", "Simonyi"], '
        '"subsystems": ["Mount", "TMA"], '
        '"components": ["ATMCS CSC"]}` will match '
        'all messages that have "AuxTel" OR '
        '"Simonyi" values under the "systems" key '
        'OR have "Mount" OR "TMA" values under the "subsystems" key '
        'OR have "ATMCS CSC" value under the "components" key. '
        'Note that setting "components_path" to `{"subsystems": '
        '["Mount", "TMA"]}` is the same as setting it to '
        '`{"subsystems": ["TMA", "Mount"]}` so will end up '
        'in the same result. Also setting it to `{"subsystems": []}` will '
        'include all messages that have at least the "subsystems" key defined. '
        "Any key with a value that is not a list will be ignored. "
        'Furthermore setting "components_path" to `{}` will have no effect and '
        "an invalid JSON will raise a 400 error.",
    ),
    exclude_components_path: None
    | str = fastapi.Query(
        default=None,
        description="Components structure in JSON format to exclude. "
        'All messages with a "components_json" field that '
        "matches at least a key with any of the values specified within "
        'the "exclude_components_path" are excluded. The JSON object '
        "represents the current hierarchy of systems, subsystems "
        "and components on the OBS Jira project: "
        '`{"systems": ["system1", ..., "systemN"], '
        '"subsystems": ["subsystem1", ..., "subsystemN"], '
        '"components": ["component1", ..., "componentN"]}`. '
        'E.g. Setting "exclude_components_path" to `{"systems": ["AuxTel", '
        '"Simonyi"], "subsystems": ["Mount", "TMA"], '
        '"components": ["ATMCS CSC"]}` will match '
        'all messages that have "AuxTel" OR '
        '"Simonyi" values under the "systems" key '
        'OR have "Mount" OR "TMA" values under the "subsystems" key '
        'OR have "ATMCS CSC" value under the "components" key. '
        'Note that setting "exclude_components_path" to `{"subsystems": '
        '["Mount", "TMA"]}` is the same as setting it to '
        '`{"subsystems": ["TMA", "Mount"]}` so will end up '
        'in the same result. Also setting it to `{"subsystems": []}` will '
        'include all messages that have at least the "subsystems" key defined. '
        "Any key with a value that is not a list will be ignored. "
        'Furthermore setting "exclude_components_path" to `{}` will have no effect '
        "and an invalid JSON will raise a 400 error.",
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
    has_date_begin: None
    | bool = fastapi.Query(
        default=None,
        description="Does this message have a non-null date_begin?",
    ),
    min_date_begin: None
    | datetime.datetime = fastapi.Query(
        default=None, description="Minimum user-specified TAI date."
    ),
    max_date_begin: None
    | datetime.datetime = fastapi.Query(
        default=None, description="Maximum user-specified TAI date."
    ),
    has_date_end: None
    | bool = fastapi.Query(
        default=None,
        description="Does this message have a non-null date_end?",
    ),
    min_date_end: None
    | datetime.datetime = fastapi.Query(
        default=None, description="Minimum user-specified TAI date."
    ),
    max_date_end: None
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
    jira_fields_table = state.narrativelog_db.jira_fields_table

    # Names of selection arguments
    select_arg_names = (
        "site_ids",
        "message_text",
        "min_level",
        "max_level",
        "user_ids",
        "user_agents",
        # 'systems' field is deprecated and will be removed in v1.0.0.
        #  Please use 'components_path' instead
        "systems",
        # 'exclude_systems' field is deprecated and will be removed in v1.0.0.
        #  Please use 'components_path' instead
        "exclude_systems",
        # 'subsystems' field is deprecated and will be removed in v1.0.0.
        #  Please use 'components_path' instead
        "subsystems",
        # 'exclude_subsystems' field is deprecated and will be removed in v1.0.0.
        #  Please use 'components_path' instead
        "exclude_subsystems",
        # 'cscs' field is deprecated and will be removed in v1.0.0.
        #  Please use 'components_path' instead
        "cscs",
        # 'exclude_cscs' field is deprecated and will be removed in v1.0.0.
        #  Please use 'components_path' instead
        "exclude_cscs",
        # 'components' field is deprecated and will be removed in v1.0.0.
        #  Please use 'components_path' instead
        "components",
        # 'exclude_components' field is deprecated and will be removed in v1.0.0.
        #  Please use 'components_path' instead
        "exclude_components",
        # 'primary_software_components' field is deprecated
        #  and will be removed in v1.0.0. Please use 'components_path' instead
        "primary_software_components",
        # 'exclude_primary_software_components' field is deprecated
        #  and will be removed in v1.0.0. Please use 'components_path' instead
        "exclude_primary_software_components",
        # 'primary_hardware_components' field is deprecated
        #  and will be removed in v1.0.0. Please use 'components_path' instead
        "primary_hardware_components",
        # 'exclude_primary_hardware_components' field is deprecated
        #  and will be removed in v1.0.0. Please use 'components_path' instead
        "exclude_primary_hardware_components",
        "components_path",
        "exclude_components_path",
        "tags",
        "exclude_tags",
        "urls",
        "min_time_lost",
        "max_time_lost",
        "has_date_begin",
        "min_date_begin",
        "max_date_begin",
        "has_date_end",
        "min_date_end",
        "max_date_end",
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
                # 'systems' field is deprecated and will be removed in v1.0.0.
                #  Please use 'components_path' instead
                "systems",
                # 'subsystems' field is deprecated and will be removed in v1.0.0.
                #  Please use 'components_path' instead
                "subsystems",
                # 'cscs' field is deprecated and will be removed in v1.0.0.
                #  Please use 'components_path' instead
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
                # 'components' field is deprecated and will be removed in v1.0.0.
                #  Please use 'components_path' instead
                "components",
                # 'primary_software_components' field is deprecated
                #  and will be removed in v1.0.0. Please use 'components_path' instead
                "primary_software_components",
                # 'primary_hardware_components' field is deprecated
                #  and will be removed in v1.0.0. Please use 'components_path' instead
                "primary_hardware_components",
            }:
                column = jira_fields_table.columns[key]
                conditions.append(column.op("&&")(value))
            elif key in {
                "exclude_tags",
                # 'exclude_systems' field is deprecated
                #  and will be removed in v1.0.0. Please use 'components_path' instead
                "exclude_systems",
                # 'exclude_subsystems' field is deprecated
                #  and will be removed in v1.0.0. Please use 'components_path' instead
                "exclude_subsystems",
                # 'exclude_cscs' field is deprecated
                #  and will be removed in v1.0.0. Please use 'components_path' instead
                "exclude_cscs",
            }:
                # Value is a list; field name is the end of the key.
                # Note: the list cannot be empty, because the array is passed
                # by listing the parameter once per value.
                column_name = key[8:]
                column = message_table.columns[column_name]
                conditions.append(sa.sql.not_(column.op("&&")(value)))
            elif key in {
                # 'exclude_components' field is deprecated
                #  and will be removed in v1.0.0. Please use 'components_path' instead
                "exclude_components",
                # 'exclude_primary_software_components' field is deprecated
                #  and will be removed in v1.0.0. Please use 'components_path' instead
                "exclude_primary_software_components",
                # 'exclude_primary_hardware_components' field is deprecated
                #  and will be removed in v1.0.0. Please use 'components_path' instead
                "exclude_primary_hardware_components",
            }:
                column_name = key[8:]
                column = jira_fields_table.columns[column_name]
                conditions.append(sa.sql.not_(column.op("&&")(value)))
            elif key in {"components_path"}:
                try:
                    parsed_value = json.loads(value)
                except json.JSONDecodeError as error:
                    raise fastapi.HTTPException(
                        status_code=http.HTTPStatus.BAD_REQUEST,
                        detail=f"Invalid JSON in {key}: {error}",
                    )
                column_name = "components_json"
                column = jira_fields_table.columns[column_name]
                individual_conditions = []
                for key in parsed_value:
                    value = parsed_value[key]
                    if not value or not isinstance(value, list):
                        continue
                    for element in value:
                        path = {key: [element]}
                        individual_conditions.append(column.contains(path))
                conditions.append(sa.sql.or_(*individual_conditions))
            elif key in {"exclude_components_path"}:
                try:
                    parsed_value = json.loads(value)
                except json.JSONDecodeError as error:
                    raise fastapi.HTTPException(
                        status_code=http.HTTPStatus.BAD_REQUEST,
                        detail=f"Invalid JSON in {key}: {error}",
                    )
                column_name = "components_json"
                column = jira_fields_table.columns[column_name]
                individual_conditions = []
                for key in parsed_value:
                    value = parsed_value[key]
                    if not value or not isinstance(value, list):
                        continue
                    for element in value:
                        path = {key: [element]}
                        individual_conditions.append(column.contains(path))
                conditions.append(
                    sa.sql.not_(sa.sql.or_(*individual_conditions))
                )
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
            message_table
            # Join with jira_fields table
            .join(jira_fields_table, isouter=True)
            .select()
            .where(full_conditions)
            .order_by(*order_by_columns)
            .limit(limit)
            .offset(offset)
        )
        rows = result.fetchall()

        return [Message.from_orm(row) for row in rows]

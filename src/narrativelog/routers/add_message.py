__all__ = ["add_message"]

import datetime
import http

import astropy.time
import fastapi
import sqlalchemy as sa

from ..message import Message
from ..shared_state import SharedState, get_shared_state
from ..utils import JIRA_OBS_SYSTEMS_HIERARCHY_MARKDOWN_LINK
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
    category: None
    | str = fastapi.Body(
        default=None,
        description="Message category; a string.",
    ),
    time_lost_type: None
    | str = fastapi.Body(
        default=None,
        description="Type of lost time.",
    ),
    tags: list[str] = fastapi.Body(
        default=[],
        description="Tags describing the message. " + TAG_DESCRIPTION,
    ),
    systems: None
    | list[str] = fastapi.Body(
        default=None,
        description="Zero or more systems to which the message applies. "
        "**This field is deprecated and will be removed in v1.0.0**. "
        "Please use 'components_json' instead.",
    ),
    subsystems: None
    | list[str] = fastapi.Body(
        default=None,
        description="Zero or more subsystems to which the message applies. "
        "**This field is deprecated and will be removed in v1.0.0**. "
        "Please use 'components_json' instead.",
    ),
    cscs: None
    | list[str] = fastapi.Body(
        default=None,
        description="Zero or more CSCs to which the message applies. "
        "Each entry should be in the form 'name' or 'name:index', "
        "where 'name' is the SAL component name and 'index' is the SAL index. "
        "**This field is deprecated and will be removed in v1.0.0**. "
        "Please use 'components_json' instead.",
    ),
    components: None
    | list[str] = fastapi.Body(
        default=None,
        description="Zero or more components to which the message applies. "
        "Each entry should be a valid component name entry on the OBS jira project. "
        "**This field is deprecated and will be removed in v1.0.0**. "
        "Please use 'components_json' instead.",
    ),
    primary_software_components: None
    | list[str] = fastapi.Body(
        default=None,
        description="Primary software components to which the message applies. "
        "Each entry should be a valid component name entry on the OBS jira project. "
        "**This field is deprecated and will be removed in v1.0.0**. "
        "Please use 'components_json' instead.",
    ),
    primary_hardware_components: None
    | list[str] = fastapi.Body(
        default=None,
        description="Primary hardware components to which the message applies. "
        "Each entry should be a valid component name entry on the OBS jira project. "
        "**This field is deprecated and will be removed in v1.0.0**. "
        "Please use 'components_json' instead.",
    ),
    components_json: None
    | dict = fastapi.Body(
        default=None,
        description="""
JSON representation of systems, subsystems and components hierarchy
 on the OBS jira project. An example of a valid payload is:

    {
        "name": "AuxTel",
        "children": [
            {
                "name": "Dome",
                "children": [
                    {
                        "name": "AT Azimuth Drives"
                    }
                ]
            }
        ]
    }

For a full list of valid systems, subsystems and components please refer to: """
        f"""{JIRA_OBS_SYSTEMS_HIERARCHY_MARKDOWN_LINK}.""",
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
    date_begin: None
    | datetime.datetime = fastapi.Body(
        default=None,
        description="Approximate initial TAI date "
        "at which is relevant "
        "(if different than the time at which the message was specified). "
        "Specify as an ISO 8601 string with no time zone suffix (not even Z).",
    ),
    date_end: None
    | datetime.datetime = fastapi.Body(
        default=None,
        description="Approximate final TAI date "
        "at which is relevant. "
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

    for date_arg, date_arg_name in (
        (date_begin, "date_begin"),
        (date_end, "date_end"),
    ):
        if date_arg is not None and date_arg.tzinfo is not None:
            # Note:  I don't know how to make the router accept dates with
            # any time zone other than None (no suffix, good) or UTC
            # (suffix Z, bad because UTC is not TAI).
            # Appending ±hh.mm is rejected before the router runs.
            # But in any case reject all time zones.
            raise fastapi.HTTPException(
                status_code=http.HTTPStatus.BAD_REQUEST,
                detail=f"{date_arg_name} must not have a time zone suffix",
            )

    tags = normalize_tags(tags)

    message_table = state.narrativelog_db.message_table
    jira_fields_table = state.narrativelog_db.jira_fields_table
    async with state.narrativelog_db.engine.begin() as connection:
        # Add the message.
        result_message = await connection.execute(
            message_table.insert()
            .values(
                site_id=state.site_id,
                message_text=message_text,
                level=level,
                tags=tags,
                urls=urls,
                time_lost=time_lost,
                date_begin=date_begin,
                date_end=date_end,
                user_id=user_id,
                user_agent=user_agent,
                is_human=is_human,
                date_added=curr_tai.tai.datetime,
                # 'systems' field is deprecated and will be removed in v1.0.0.
                #  Please use 'components_json' instead
                systems=systems,
                # 'subsystems' field is deprecated and will be removed in v1.0.0.
                #  Please use 'components_json' instead
                subsystems=subsystems,
                # 'cscs' field is deprecated and will be removed in v1.0.0.
                #  Please use 'components_json' instead
                cscs=cscs,
                category=category,
                time_lost_type=time_lost_type,
            )
            .returning(sa.literal_column("*"))
        )
        row_message = result_message.fetchone()
        if row_message is None:
            raise fastapi.HTTPException(
                status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
                detail="Couldn't create message entry",
            )

        # Add the jira fields
        if any(
            field is not None
            for field in (
                # 'components' field is deprecated and will be removed in v1.0.0.
                #  Please use 'components_json' instead
                components,
                # 'primary_software_components' field is deprecated
                #  and will be removed in v1.0.0. Please use 'components_json' instead
                primary_software_components,
                # 'primary_hardware_components' field is deprecated
                #  and will be removed in v1.0.0. Please use 'components_json' instead
                primary_hardware_components,
                components_json,
            )
        ):
            result_jira_fields = await connection.execute(
                jira_fields_table.insert()
                .values(
                    # 'components' field is deprecated and will be removed in v1.0.0.
                    #  Please use 'components_json' instead
                    components=components,
                    # 'primary_software_components' field is deprecated
                    #  and will be removed in v1.0.0.
                    #  Please use 'components_json' instead
                    primary_software_components=primary_software_components,
                    # 'primary_hardware_components' field is deprecated
                    #  and will be removed in v1.0.0.
                    #  Please use 'components_json' instead
                    primary_hardware_components=primary_hardware_components,
                    components_json=components_json,
                    message_id=row_message.id,
                )
                .returning(sa.literal_column("*"))
            )
            row_jira_fields = result_jira_fields.fetchone()

            if row_jira_fields is None:
                raise fastapi.HTTPException(
                    status_code=http.HTTPStatus.INTERNAL_SERVER_ERROR,
                    detail="Couldn't create jira_fields entry for message",
                )

        # Find the message and join with jira_fields
        result_message_joined = await connection.execute(
            message_table
            # Join with jira_fields_table
            .join(jira_fields_table, isouter=True)
            .select()
            .where(message_table.c.id == row_message.id)
        )
        row = result_message_joined.fetchone()

        return Message.from_orm(row)

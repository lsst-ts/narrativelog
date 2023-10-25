__all__ = ["Message", "MESSAGE_FIELDS", "MESSAGE_ORDER_BY_VALUES"]

import datetime
import uuid

from pydantic import BaseModel, Field


class Message(BaseModel):
    id: uuid.UUID = Field(title="Message ID: a UUID that is the primary key.")
    site_id: str = Field(title="Site at which the message was created.")
    message_text: str = Field(title="Message.")
    level: int = Field(
        title="Message level. A python logging level: "
        "info=20, warning=30, error=40."
    )
    tags: list[str] = Field(
        title="Zero or more space-separated keywords relevant to this message."
    )
    urls: list[str] = Field(
        title="Zero or more space-separated URLS to JIRA tickets, screen shots, etc."
    )
    time_lost: datetime.timedelta = Field(
        title="Estimate of lost on-sky time."
    )
    date_begin: None | datetime.datetime = Field(
        title="Approximate initial TAI date at which the message is relevant "
        "(if different than the time at which the message was specified)"
    )
    user_id: str = Field(title="User ID.")
    user_agent: str = Field(
        title="User agent: the application that created the message."
    )
    is_human: bool = Field(title="Was it a human who created the message?")
    is_valid: bool = Field(
        title="Is this message still valid (false if deleted or edited)."
    )
    date_added: datetime.datetime = Field(
        title="TAI date at which the message was added."
    )
    date_invalidated: None | datetime.datetime = Field(
        title="TAI date at which is_valid was last set true."
    )
    parent_id: None | uuid.UUID = Field(
        title="Message ID of message this is an edited version of."
    )
    # Added 2022-07-19
    systems: None | list[str] = Field(
        title="Zero or more system names.",
    )
    subsystems: None | list[str] = Field(title="Zero or more subsystem names.")
    cscs: None | list[str] = Field(
        title="Zero or more CSCs names. "
        "Each entry should be in the form 'name' or 'name:index', "
        "where 'name' is the SAL component name and 'index' is the SAL index."
    )
    # Added 2022-07-27
    date_end: None | datetime.datetime = Field(
        title="Approximate final TAI date at which the message is relevant"
    )
    # Added 2023-08-10
    components: None | list[str] = Field(
        title="Zero or more component names. "
        "Each entry should be a valid component name entry on the OBS jira project.",
    )
    primary_software_components: None | list[str] = Field(
        title="Zero or more primary software component names. "
        "Each entry should be a valid component name entry on the OBS jira project.",
    )
    primary_hardware_components: None | list[str] = Field(
        title="Zero or more primary hardware component names. "
        "Each entry should be a valid component name entry on the OBS jira project.",
    )
    # Added 2023-10-24
    category: None | str = Field(
        title="Category of message.",
    )
    time_lost_type: None | str = Field(
        title="Type of time lost.",
    )

    class Config:
        orm_mode = True
        from_attributes = True


JIRA_FIELDS = (
    "components",
    "primary_software_components",
    "primary_hardware_components",
)
MESSAGE_FIELDS = tuple(
    set(Message.schema()["properties"].keys()) - set(JIRA_FIELDS)
)


def _make_message_order_by_values() -> tuple[str, ...]:
    """Make a tuple of valid order_by values for find_messages.

    Return a tuple of all field names,
    plus those same field names with a leading "-".
    """
    order_by_values = []
    for field in Message.schema()["properties"]:
        order_by_values += [field, "-" + field]
    return tuple(order_by_values)


# Tuple of valid order_by fields.
# Each of these exists in the Message class.
MESSAGE_ORDER_BY_VALUES = _make_message_order_by_values()

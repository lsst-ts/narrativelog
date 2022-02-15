__all__ = ["Message", "MESSAGE_FIELDS"]

import datetime
import typing
import uuid

import pydantic


class Message(pydantic.BaseModel):
    id: uuid.UUID = pydantic.Field(
        title="Message ID: a UUID that is the primary key."
    )
    site_id: str = pydantic.Field(
        title="Site at which the message was created."
    )
    message_text: str = pydantic.Field(title="Message.")
    level: int = pydantic.Field(
        title="Message level. A python logging level: "
        "info=20, warning=30, error=40."
    )
    tags: typing.List[str] = pydantic.Field(
        title="Zero or more space-separated keywords relevant to this message."
    )
    urls: typing.List[str] = pydantic.Field(
        title="Zero or more space-separated URLS to JIRA tickets, screen shots, etc."
    )
    time_lost: datetime.timedelta = pydantic.Field(
        title="Estimate of lost on-sky time."
    )
    date_user_specified: typing.Optional[datetime.datetime] = pydantic.Field(
        title="Approximate TAI date at which this message is relevant "
        "(if different than the time at which the message was specified)"
    )
    user_id: str = pydantic.Field(title="User ID.")
    user_agent: str = pydantic.Field(
        title="User agent: the application that created the message."
    )
    is_human: bool = pydantic.Field(
        title="Was it a human who created the message?"
    )
    is_valid: bool = pydantic.Field(
        title="Is this message still valid (false if deleted or edited)."
    )
    date_added: datetime.datetime = pydantic.Field(
        title="TAI date at which the message was added."
    )
    date_invalidated: typing.Optional[datetime.datetime] = pydantic.Field(
        title="TAI date at which is_valid was last set true."
    )
    parent_id: typing.Optional[uuid.UUID] = pydantic.Field(
        title="Message ID of message this is an edited version of."
    )

    class Config:
        orm_mode = True


MESSAGE_FIELDS = tuple(Message.schema()["properties"].keys())

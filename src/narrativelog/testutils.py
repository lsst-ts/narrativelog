__all__ = [
    "TEST_SITE_ID",
    "TEST_TAGS",
    "TEST_URLS",
    "TEST_SYSTEMS",
    "TEST_SUBSYSTEMS",
    "TEST_CSCS",
    "MessageDictT",
    "assert_good_response",
    "assert_messages_equal",
    "cast_special",
    "create_test_client",
    "modify_environ",
]

import collections.abc
import contextlib
import datetime
import http
import os
import random
import typing
import unittest.mock
import uuid

import astropy.time
import httpx
import sqlalchemy.engine
import testing.postgresql
from sqlalchemy import MetaData, literal_column
from sqlalchemy.ext.asyncio import create_async_engine

from . import main, shared_state
from .create_tables import create_jira_fields_table, create_message_table
from .message import JIRA_FIELDS, MESSAGE_FIELDS

# Range of dates for random messages.
MIN_DATE_RANDOM_MESSAGE = "2021-01-01"
MAX_DATE_RANDOM_MESSAGE = "2022-12-31"
MAX_TIME_DELTA_RANDOM_MESSAGE = datetime.timedelta(days=2)

TEST_SITE_ID = "test"
TEST_TAGS = "green eggs and ham".split()
TEST_URLS = [
    "https://jira.lsstcorp.org/browse/DM-1",
    "https://jira.lsstcorp.org/browse/DM-3",
    "https://jira.lsstcorp.org/browse/DM-5",
    "https://jira.lsstcorp.org/browse/DM-7",
]
TEST_SYSTEMS = [f"system{n}" for n in range(10)]
TEST_SUBSYSTEMS = [f"subsystem{n}" for n in range(20)]
TEST_CSCS = (
    "ATDome ATMCS ESS MTDome MTHexapod:1 MTHexapod:2 MTMount MTM1M3".split()
)
TEST_COMPONENTS = [f"component{n}" for n in range(10)]
TEST_PRIMARY_SOFTWARE_COMPONENTS = [
    f"primary_software_component{n}" for n in range(10)
]
TEST_PRIMARY_HARDWARE_COMPONENTS = [
    f"primary_hardware_component{n}" for n in range(10)
]

# Type annotation aliases
MessageDictT = dict[str, typing.Any]
ArgDictT = dict[str, typing.Any]

random.seed(47)


@contextlib.asynccontextmanager
async def create_test_client(
    num_messages: int = 0,
    num_edited: int = 0,
) -> collections.abc.AsyncGenerator[
    tuple[httpx.AsyncClient, list[MessageDictT]], None
]:
    """Create the test database, test server, and httpx client."""
    with testing.postgresql.Postgresql() as postgresql:
        messages = await create_test_database(
            postgres_url=postgresql.url(),
            num_messages=num_messages,
            num_edited=num_edited,
        )

        db_config = db_config_from_dsn(postgresql.dsn())
        with modify_environ(
            SITE_ID=TEST_SITE_ID,
            **db_config,
        ):
            # Note: httpx.AsyncClient does not trigger startup and shutdown
            # events. We could use asgi-lifespan's LifespanManager,
            # but it does not trigger the shutdown event if there is
            # an exception, so it does not seem worth the bother.
            assert not shared_state.has_shared_state()
            await main.startup_event()
            try:
                async with httpx.AsyncClient(
                    app=main.app, base_url="http://test"
                ) as client:
                    assert shared_state.has_shared_state()
                    yield client, messages
            finally:
                await main.shutdown_event()


@contextlib.contextmanager
def modify_environ(**kwargs: typing.Any) -> collections.abc.Iterator:
    """Context manager to temporarily patch os.environ.

    This calls `unittest.mock.patch` and is only intended for unit tests.

    Parameters
    ----------
    kwargs : `dict` [`str`, `str` or `None`]
        Environment variables to set or clear.
        Each key is the name of an environment variable (with correct case);
        it need not already exist. Each value must be one of:

        * A string value to set the env variable.
        * None to delete the env variable, if present.

    Raises
    ------
    RuntimeError
        If any value in kwargs is not of type `str` or `None`.

    Notes
    -----
    Example of use::

        ...
        def test_foo(self):
            set_value = "Value for $ENV_TO_SET"
            with modify_environ(
                HOME=None,  # Delete this env var
                ENV_TO_SET=set_value,  # Set this env var
            ):
                self.assertNotIn("HOME", os.environ)
                self.assert(os.environ["ENV_TO_SET"], set_value)
    """
    bad_value_strs = [
        f"{name}: {value!r}"
        for name, value in kwargs.items()
        if not isinstance(value, str) and value is not None
    ]
    if bad_value_strs:
        raise RuntimeError(
            "The following arguments are not of type str or None: "
            + ", ".join(bad_value_strs)
        )

    new_environ = os.environ.copy()
    for name, value in kwargs.items():
        if value is None:
            new_environ.pop(name, None)
        else:
            new_environ[name] = value
    with unittest.mock.patch("os.environ", new_environ):
        yield


def assert_good_response(response: httpx.Response) -> typing.Any:
    """Assert that a response is good and return the data.

    Parameters
    ----------
    command
        The command. If None then return the whole response, else return
        the response from the command (response["data"][command]) --
        a single message dict or a list of message dicts.
    """
    assert (
        response.status_code == http.HTTPStatus.OK
    ), f"Bad response {response.status_code}: {response.text}"
    data = response.json()
    assert "errors" not in data, f"errors={data['errors']}"
    return data


def assert_messages_equal(
    message1: MessageDictT, message2: MessageDictT
) -> None:
    """Assert that two messages are identical.

    Handle the "id" field specially because it may be a uuid.UUID or a str.
    Handle date fields specially because they may be datetime.datetime
    or ISOT strings.
    Handle timedelta fields specially they may be datetime.timedelta
    or float seconds.
    """
    assert message1.keys() == message2.keys()
    for field in message1:
        values = [
            cast_special(value) for value in (message1[field], message2[field])
        ]
        assert (
            values[0] == values[1]
        ), f"field {field} unequal: {values[0]!r} != {values[1]!r}"


def cast_special(value: typing.Any) -> typing.Any:
    """Cast special types to plain data types;
    return plain old data types unchanged.

    This allows comparison between values in the database
    and values returned by the web API.

    The special types are:

    * datetime.datetime: converted to an ISO string with "T" separator.
    * datetime.timedela: converted to float seconds.
    * uuid.UUID: convert to a string.
    """
    if isinstance(value, datetime.datetime):
        return value.isoformat(sep="T")
    elif isinstance(value, datetime.timedelta):
        return value.total_seconds()
    elif isinstance(value, uuid.UUID):
        return str(value)
    return value


def db_config_from_dsn(dsn: dict[str, str]) -> dict[str, str]:
    """Get app database configuration arguments from a database dsn.

    The intended usage is to configure the application
    from an instance of testing.postgresql.Postgresql()::

        with testing.postgresql.Postgresql() as postgresql:
            create_test_database(postgresql.url(), num_messages=0)

            db_config = db_config_from_dsn(postgresql.dsn())
            with modify_environ(
                SITE_ID=TEST_SITE_ID,
                **db_config,
            ):
                import narrativelog.app

                client = fastapi.testclient.TestClient(narrativelog.main.app)
    """
    assert dsn.keys() <= {"port", "host", "user", "database"}
    return {
        f"narrativelog_db_{key}".upper(): str(value)
        for key, value in dsn.items()
    }


def random_bool() -> bool:
    """Return a random bool."""
    return random.random() > 0.5


def random_date(precision: int = 0) -> datetime.datetime:
    """Return a random date between MIN_DATE_RANDOM_MESSAGE
    and MAX_DATE_RANDOM_MESSAGE.

    Parameters
    ----------
    precision
        The number of decimal digits of seconds.
        If 0 then the output has no decimal point after the seconds field.

    Return the same format as dates returned from the database.
    """
    min_date_unix = astropy.time.Time(MIN_DATE_RANDOM_MESSAGE).unix
    max_date_unix = astropy.time.Time(MAX_DATE_RANDOM_MESSAGE).unix
    dsec = max_date_unix - min_date_unix
    unix_time = min_date_unix + random.random() * dsec
    return astropy.time.Time(
        unix_time, format="unix", precision=precision
    ).datetime


def random_duration(precision: int = 0) -> datetime.timedelta:
    """Return a random duration. Half of the time return duration=0.

    Parameters
    ----------
    precision : int
        Number of digits after the decimal point of seconds.

    Returns the same format as durations returned from the database.
    """
    if random.random() > 0.5:
        return datetime.timedelta()
    dsec = MAX_TIME_DELTA_RANDOM_MESSAGE.total_seconds()
    duration_sec = round(random.random() * dsec, precision)
    return datetime.timedelta(seconds=duration_sec)


def random_str(nchar: int) -> str:
    """Return a random string of nchar printable UTF-8 characters.

    The list of characters is limited, but attempts to
    cover a wide range of potentially problematic characters
    including ' " \t \n \\ and an assortment of non-ASCII characters.
    """
    chars = list(
        "abcdefgABCDEFG012345 \t\n\r"
        "'\"“”`~!@#$%^&*()-_=+[]{}\\|,.<>/?"
        "¡™£¢∞§¶•ªº–≠“‘”’«»…ÚæÆ≤¯≥˘÷¿"
        "œŒ∑„®‰†ˇ¥ÁüîøØπ∏åÅßÍ∂ÎƒÏ©˝˙Ó∆Ô˚¬ÒΩ¸≈˛çÇ√◊∫ıñµÂ"
        "✅😀⭐️🌈🌎1️⃣🟢❖🍏🪐💫🥕🥑🌮🥗🚠🚞🚀⚓️🚁🚄🏝🧭🕰📡🗝📅🖋🔎❤️☮️"
    )
    return "".join(random.sample(chars, nchar))


def random_strings(words: list[str], max_num: int = 3) -> list[str]:
    """Return a list of 0 or more strings from a list of strings.

    Parameters
    ----------
    strings
        List of strings from which to select returned strings.
    max_num
        The maximum number of returned strings.

    Half of the time it will return 0 items.
    The rest of the time it will return 1 - max_num values
    in random order, with equal probability per number of returned strings.
    """
    if random.random() < 0.5:
        return []
    num_to_return = random.randint(1, max_num)
    return random.sample(words, num_to_return)


def random_message() -> MessageDictT:
    """Make one random message, as a dict of field: value.

    All messages will have ``id=None``, ``site_id=TEST_SITE_ID``,
    ``is_valid=True``, ``date_invalidated=None``, and ``parent_id=None``.

    Fields are in the same order as `Message` and the database schema,
    to make it easier to visually compare these messages to messages in
    responses.

    String are random unicode characters. Tags and urls are generated from
    a random selection (of random length) of possible tags and URLs.

    To use:

    * Call multiple times to make a list of messages.
    * Sort that list by ``date_added``.
    * Add the ``id`` field, in order, starting at 1.
    * Optionally modify some messages to be edited versions
      of earlier messages, as follows:

      * Set edited_message["parent_id"] = parent_message["id"]
      * Set parent_message["is_valid"] = False
      * Set parent_message["date_invalidated"] =
        edited_message["date_added"]
    """
    random_value = random.random()
    date_begin = None
    date_end = None
    if random_value > 0.75:
        date_begin = random_date()
        date_end = date_begin + random_duration()
    elif random_value > 0.5:
        date_end = random_date()
    elif random_value > 0.25:
        date_begin = random_date()

    message = dict(
        id=None,
        site_id=TEST_SITE_ID,
        message_text=random_str(nchar=20),
        level=random.randint(0, 40),
        tags=random_strings(TEST_TAGS),
        urls=random_strings(TEST_URLS),
        time_lost=random_duration(),
        date_begin=date_begin,
        user_id=random_str(nchar=14),
        user_agent=random_str(nchar=12),
        is_human=random_bool(),
        is_valid=True,
        date_added=random_date(),
        date_invalidated=None,
        parent_id=None,
        # Added 2022-07-19
        systems=random_strings(TEST_SYSTEMS),
        subsystems=random_strings(TEST_SUBSYSTEMS),
        cscs=random_strings(TEST_CSCS),
        # Added 2022-07-27
        date_end=date_end,
        # Added 2023-08-10
        components=random_strings(TEST_COMPONENTS),
        primary_software_components=random_strings(
            TEST_PRIMARY_SOFTWARE_COMPONENTS
        ),
        primary_hardware_components=random_strings(
            TEST_PRIMARY_HARDWARE_COMPONENTS
        ),
    )

    # Check that we have set all fields (not necessarily in order).
    assert set(message) == (set(MESSAGE_FIELDS) | set(JIRA_FIELDS))

    return message


def random_messages(num_messages: int, num_edited: int) -> list[MessageDictT]:
    """Make a list of random messages, each a dict of field: value.

    Parameters
    ----------
    num_messages
        Number of messages
    num_edited
        Number of these messages that should be edited versions
        of earlier messages.

    Notes
    -----

    The list will be in order of increasing ``date_added``.

    Link about half of the messages to an older message.
    """
    message_list = [random_message() for i in range(num_messages)]
    message_list.sort(key=lambda message: message["date_added"])
    for i, message in enumerate(message_list):
        message["id"] = uuid.uuid4()

    # Create edited messages.
    parent_message_id_set: set[uuid.UUID] = set()
    edited_messages: list[MessageDictT] = list(
        # [1:] because there is no older message to be the parent.
        random.sample(message_list[1:], num_edited)
    )
    edited_messages.sort(key=lambda message: message["date_added"])
    for i, message in enumerate(edited_messages):
        while True:
            parent_message = random.choice(message_list[0 : i + 1])
            if parent_message["id"] not in parent_message_id_set:
                parent_message_id_set.add(parent_message["id"])
                break
        message["parent_id"] = parent_message["id"]
        parent_message["is_valid"] = False
        parent_message["date_invalidated"] = message["date_added"]
    return message_list


async def create_test_database(
    postgres_url: str,
    num_messages: int,
    num_edited: int = 0,
) -> list[MessageDictT]:
    """Create a test database, initialize it with random messages,
    and return the messages.

    Parameters
    ----------
    postgresql_url
        URL to PostgreSQL database. Typically a test database created using::

            with testing.postgresql.Postgresql() as postgresql:
                postgres_url = postgresql.url()
    num_messages
        Number of messages
    num_edited, optional
        Number of these messages that should be edited versions
        of earlier messages. Must be 0 or < ``num_messages``.

    Returns
    -------
    messages
        The randomly created messages. Each message is a dict of field: value
        and all fields are set.
    """
    if num_edited > 0 and num_edited >= num_messages:
        raise ValueError(
            f"num_edited={num_edited} must be zero or "
            f"less than num_messages={num_messages}"
        )
    sa_url = sqlalchemy.engine.make_url(postgres_url)
    sa_url = sa_url.set(drivername="postgresql+asyncpg")
    engine = create_async_engine(sa_url, future=True)

    sa_metadata = MetaData()
    table_message = create_message_table(sa_metadata)
    table_jira_fields = create_jira_fields_table(sa_metadata)
    async with engine.begin() as connection:
        # await connection.run_sync(table_message.metadata.create_all)
        await connection.run_sync(sa_metadata.create_all)

    messages = random_messages(
        num_messages=num_messages, num_edited=num_edited
    )
    async with engine.begin() as connection:
        for message in messages:
            # Insert the jira fields
            result_jira_fields = await connection.execute(
                table_jira_fields.insert()
                .values(
                    components=message["components"],
                    primary_software_components=message[
                        "primary_software_components"
                    ],
                    primary_hardware_components=message[
                        "primary_hardware_components"
                    ],
                )
                .returning(literal_column("*"))
            )
            data_jira_fields = result_jira_fields.fetchone()
            assert data_jira_fields is not None

            # Do not insert the "is_valid" field
            # because it is computed.
            pruned_message = message.copy()
            del pruned_message["is_valid"]
            # Do not insert "components",
            # "primary_software_components", or "primary_hardware_components"
            # because they are in a separate table.
            del pruned_message["components"]
            del pruned_message["primary_software_components"]
            del pruned_message["primary_hardware_components"]

            # Insert the message
            result_message = await connection.execute(
                table_message.insert()
                .values(
                    **pruned_message,
                    jira_fields_id=data_jira_fields.id,
                )
                .returning(table_message.c.id, table_message.c.is_valid)
            )
            data_message = result_message.fetchone()
            assert message["id"] == data_message.id
            assert message["is_valid"] == data_message.is_valid

    return messages

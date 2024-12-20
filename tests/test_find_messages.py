import collections.abc
import http
import itertools
import json
import random
import typing
import unittest

import httpx

from narrativelog.message import MESSAGE_FIELDS
from narrativelog.testutils import (
    MessageDictT,
    assert_good_response,
    assert_messages_equal,
    cast_special,
    create_test_client,
)

random.seed(11)


class doc_str:
    """Decorator to add a doc string to a function.

    Unlike the standard technique, this works with f strings
    """

    def __init__(self, doc: str):
        self.doc = doc

    def __call__(
        self, func: collections.abc.Callable
    ) -> collections.abc.Callable:
        func.__doc__ = self.doc
        return func


def assert_good_find_response(
    response: httpx.Response,
    messages: list[MessageDictT],
    predicate: collections.abc.Callable,
) -> list[MessageDictT]:
    """Assert that the correct messages were found.

    Parameters
    ----------
    response
        Response from find_messages command.
    messages
        All messages in the database (in any order).
    predicate
        Callable that takes one message and returns True if a message
        meets the find criteria, False if not.

    Returns
    found_messages
        The found messages.
    """
    found_messages = assert_good_response(response)
    for message in found_messages:
        assert predicate(
            message
        ), f"message {message} does not match {predicate.__doc__}"
    missing_messages = get_missing_message(messages, found_messages)
    for message in missing_messages:
        assert not predicate(
            message
        ), f"message {message} matches {predicate.__doc__}"

    return found_messages


def assert_messages_ordered(
    messages: list[MessageDictT], order_by: list[str]
) -> None:
    """Assert that a list of message is ordered as specified.

    Parameters
    ----------
    messages
        Messages to test
    order_by
        Field names by which the data should be ordered.
        Each name can be prefixed by "-" to mean descending order.
    """
    full_order_by = list(order_by)
    if not ("id" in order_by or "-id" in order_by):
        full_order_by.append("id")
    message1: None | dict = None
    for message2 in messages:
        if message1 is not None:
            assert_two_messages_ordered(
                message1=message1,
                message2=message2,
                order_by=full_order_by,
            )
        message1 = message2


def assert_two_messages_ordered(
    message1: MessageDictT, message2: MessageDictT, order_by: list[str]
) -> None:
    """Assert that two messages are ordered as specified.

    Parameters
    ----------
    message1
        A message.
    message2
        The next message.
    order_by
        Field names by which the data should be ordered.
        Each name can be prefixed by "-" to mean descending order.
    """
    for key in order_by:
        if key.startswith("-"):
            field = key[1:]
            desired_cmp_result = 1
        else:
            field = key
            desired_cmp_result = -1
        val1 = message1[field]
        val2 = message2[field]
        cmp_result = cmp_message_field(field, val1, val2)
        if cmp_result == desired_cmp_result:
            # These two messages are fine
            return
        elif cmp_result != 0:
            raise AssertionError(
                f"messages mis-ordered in key {key}: "
                f"message1[{field!r}]={val1!r}, message2[{field!r}]={val2!r}"
            )


def cmp_message_field(field: str, val1: typing.Any, val2: typing.Any) -> int:
    """Return -1 if val1 < val2, 0 if val1 == val2, 1 if val1 > val2.

    Value None is equal to None and larger than every value.
    This mimics how PostgreSQL handles NULL.
    """
    if val1 == val2:
        return 0
    elif val1 is None:
        return 1
    elif val2 is None:
        return -1
    elif val1 > val2:
        return 1
    return -1


def get_missing_message(
    messages: list[MessageDictT],
    found_messages: list[MessageDictT],
) -> list[MessageDictT]:
    """Get messages that were not found."""
    found_ids = set(found_message["id"] for found_message in found_messages)
    return [
        message for message in messages if str(message["id"]) not in found_ids
    ]


class FindMessagesTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_find_messages(self) -> None:
        num_messages = 12
        num_edited = 6  # Must be at least 4 in order to test ranges.
        async with create_test_client(
            num_messages=num_messages, num_edited=num_edited
        ) as (
            client,
            messages,
        ):
            # Make a list of find arguments and associated predicates.
            # Each entry is a tuple of:
            # * dict of find arg name: value
            # * predicate: function that takes a message dict
            #   and returns True if the message matches the query
            find_args_predicates: list[
                tuple[dict[str, typing.Any], collections.abc.Callable]
            ] = list()

            # Range arguments: min_<field>, max_<field>.
            for field in (
                "level",
                "date_added",
                "date_invalidated",
            ):
                values = sorted(
                    message[field]
                    for message in messages
                    if message[field] is not None
                )
                assert len(values) >= 4, f"not enough values for {field}"
                min_name = f"min_{field}"
                max_name = f"max_{field}"
                min_value = values[1]
                max_value = values[-1]
                assert max_value > min_value

                @doc_str(f"message[{field!r}] not None and >= {min_value}.")
                def test_min(
                    message: MessageDictT,
                    field: str = field,
                    min_value: typing.Any = min_value,
                ) -> bool:
                    min_value = cast_special(min_value)
                    value = cast_special(message[field])
                    return value is not None and value >= min_value

                @doc_str(f"message[{field!r}] not None and < {max_value}.")
                def test_max(
                    message: MessageDictT,
                    field: str = field,
                    max_value: typing.Any = max_value,
                ) -> bool:
                    max_value = cast_special(max_value)
                    value = cast_special(message[field])
                    return value is not None and value < max_value

                find_args_predicates += [
                    ({min_name: min_value}, test_min),
                    ({max_name: max_value}, test_max),
                ]

                # Test that an empty range (max <= min) returns no messages.
                # There is no point combining this with other tests,
                # so test it now instead of adding it to find_args_predicates.
                empty_range_args = {min_name: min_value, max_name: min_value}
                response = await client.get(
                    "/narrativelog/messages",
                    params=empty_range_args,
                )
                found_messages = assert_good_response(response)
                assert len(found_messages) == 0

            # Collection arguments for arrays;
            # <field>, with a list of values.
            for field in (
                "tags",
                "systems",
                "subsystems",
                "components",
                "primary_software_components",
                "primary_hardware_components",
                "cscs",
                "urls",
            ):
                # Scramble the messages and use two field list values
                # from the first message with at least two values
                messages_to_search = random.sample(messages, len(messages))
                for message in messages_to_search:
                    if len(message[field]) >= 2:
                        values = message[field][0:1]
                        break

                @doc_str(f"message[{field!r}] overlaps {values}")
                def test_collection(
                    message: MessageDictT,
                    field: str = field,
                    values: list[typing.Any] = values,
                ) -> bool:
                    return bool(set(message[field]) & set(values))

                arg_name = field
                find_args_predicates.append(
                    ({arg_name: values}, test_collection)
                )

            # exclude_key for collection arguments for arrays
            for field in (
                "tags",
                "systems",
                "subsystems",
                "cscs",
                "components",
                "primary_software_components",
                "primary_hardware_components",
            ):
                # Scramble the messages and use two field list values
                # from the first message with at least two values
                messages_to_search = random.sample(messages, len(messages))
                for message in messages_to_search:
                    if len(message[field]) >= 2:
                        values = message[field][0:1]
                        break

                @doc_str(f"message[{field!r}] does not overlap {values}")
                def test_collection(
                    message: MessageDictT,
                    field: str = field,
                    values: list[typing.Any] = values,
                ) -> bool:
                    return not bool(set(message[field]) & set(values))

                arg_name = "exclude_" + field
                find_args_predicates.append(
                    ({arg_name: values}, test_collection)
                )

            # Collection arguments: <field>s, with a list of values.
            num_to_find = 2
            for field in (
                "user_id",
                "user_agent",
            ):
                messages_to_find = random.sample(messages, num_to_find)
                values = [message[field] for message in messages_to_find]
                arg_name = field + "s"

                @doc_str(f"message[{field!r}] in {values}")
                def test_collection(
                    message: MessageDictT,
                    field: str = field,
                    values: list[typing.Any] = values,
                ) -> bool:
                    return message[field] in values

                find_args_predicates.append(
                    ({arg_name: values}, test_collection)
                )

            # "Contains" arguments: these specify a substring to match.
            # Search for two characters out of one message,
            # in hopes more than one (though one is fine)
            # and fewer than all messages (not a good test)
            # will match.
            for field in ("message_text",):
                value = messages[2][field][1:2]
                if value == "\\":
                    # A backslash escapes the next character,
                    # so include that character, as well.
                    value = messages[2][field][1:3]

                @doc_str(f"{value!r} in message[{field!r}]")
                def test_contains(
                    message: MessageDictT,
                    field: str = field,
                    value: str = value,
                ) -> bool:
                    return value in message[field]

                find_args_predicates.append(({field: value}, test_contains))

            # "Contains" arguments for JSON fields: these specify a
            # JSON path to match.
            for field in ("components_json",):
                # Scramble the messages and use the first
                # message with at least a key with two values
                messages_to_search = random.sample(messages, len(messages))
                for message in messages_to_search:
                    components_json = message[field]
                    for key in components_json:
                        if len(components_json[key]) >= 2:
                            first_two_values = components_json[key][0:2]
                            values = [(key, val) for val in first_two_values]
                            path = json.dumps({key: first_two_values})
                            break

                @doc_str(f"{path!r} in message[{field!r}]")
                def test_contains_path(
                    message: MessageDictT,
                    field: str = field,
                    values: list[tuple[str, str]] = values,
                ) -> bool:
                    matches = [
                        val in message[field][key] for key, val in values
                    ]
                    return any(matches)

                def test_contains_exclude_path(
                    message: MessageDictT,
                    field: str = field,
                    values: list[tuple[str, str]] = values,
                ) -> bool:
                    matches = [
                        val in message[field][key] for key, val in values
                    ]
                    return not any(matches)

                find_args_predicates += [
                    ({"components_path": path}, test_contains_path),
                    (
                        {"exclude_components_path": path},
                        test_contains_exclude_path,
                    ),
                ]

            # has_<field> arguments (for fields that may be null).
            for field in (
                "date_begin",
                "date_end",
                "date_invalidated",
                "parent_id",
            ):
                arg_name = f"has_{field}"

                @doc_str(f"message[{field!r}] is not None")
                def test_has(
                    message: MessageDictT, field: str = field
                ) -> bool:
                    return message[field] is not None

                @doc_str(f"message[{field!r}] is None")
                def test_has_not(
                    message: MessageDictT, field: str = field
                ) -> bool:
                    return message[field] is None

                find_args_predicates += [
                    ({arg_name: True}, test_has),
                    ({arg_name: False}, test_has_not),
                ]

            # Tre-state boolean fields.
            for field in ("is_human", "is_valid"):

                @doc_str(f"message[{field!r}] is True")
                def test_true(
                    message: MessageDictT, field: str = field
                ) -> bool:
                    return message[field] is True

                @doc_str(f"message[{field!r}] is False")
                def test_false(
                    message: MessageDictT, field: str = field
                ) -> bool:
                    return message[field] is False

                @doc_str(f"message[{field!r}] is either")
                def test_either(
                    message: MessageDictT, field: str = field
                ) -> bool:
                    return True

                find_args_predicates += [
                    ({field: "true"}, test_true),
                    ({field: "false"}, test_false),
                    ({field: "either"}, test_either),
                ]

            # Test single requests: one entry from find_args_predicates.
            for find_args, predicate in find_args_predicates:
                response = await client.get(
                    "/narrativelog/messages", params=find_args
                )
                if "is_valid" not in find_args:
                    # Handle the fact that is_valid defaults to True
                    @doc_str(
                        f'{predicate.__doc__} and message["is_valid"] is True'
                    )
                    def predicate_and_is_valid(
                        message: MessageDictT,
                        predicate: collections.abc.Callable = predicate,
                    ) -> bool:
                        return (
                            predicate(message) and message["is_valid"] is True
                        )

                    predicate = predicate_and_is_valid
                assert_good_find_response(response, messages, predicate)

            # Test pairs of requests: two entries from find_args_predicates,
            # which are ``and``-ed together.
            for (
                (find_args1, predicate1),
                (find_args2, predicate2),
            ) in itertools.product(find_args_predicates, find_args_predicates):
                find_args = find_args1.copy()
                find_args.update(find_args2)
                if len(find_args) < len(find_args1) + len(find_args):
                    # Overlapping arguments makes the predicates invalid.
                    continue

                @doc_str(f"{predicate1.__doc__} and {predicate2.__doc__}")
                def and_predicates(
                    message: MessageDictT,
                    predicate1: collections.abc.Callable,
                    predicate2: collections.abc.Callable,
                ) -> bool:
                    return predicate1(message) and predicate2(message)

                response = await client.get(
                    "/narrativelog/messages", params=find_args
                )
                assert_good_find_response(response, messages, and_predicates)

            # Test that find with no arguments finds all is_valid messages.
            def is_valid_predicate(message: MessageDictT) -> bool:
                """message["is_valid"] is True"""
                return message["is_valid"] is True

            response = await client.get(
                "/narrativelog/messages", params=dict()
            )
            messages = assert_good_response(response)
            assert_good_find_response(response, messages, is_valid_predicate)

            # Check order_by one field
            # Note: SQL databases sort strings differently than Python.
            # Rather than try to mimic Postgresql's sorting in Python,
            # I issue the order_by command but do not test the resulting
            # order if ordering by a string field.
            fields = list(MESSAGE_FIELDS)
            str_fields = set(
                (
                    "message_text",
                    "level",
                    "user_id",
                    "user_agent",
                    "category",
                    "time_lost_type",
                )
            )
            for field, prefix in itertools.product(fields, ("", "-")):
                order_by = [prefix + field]
                find_args = dict()
                find_args["order_by"] = order_by
                response = await client.get(
                    "/narrativelog/messages", params=find_args
                )
                messages = assert_good_response(response)
                if field not in str_fields:
                    assert_messages_ordered(
                        messages=messages, order_by=order_by
                    )

                paged_messages: list[MessageDictT] = []
                limit = 2
                find_args["limit"] = limit
                while len(paged_messages) < len(messages):
                    num_remaining = len(messages) - len(paged_messages)
                    # Check limit and offset
                    response = await client.get(
                        "/narrativelog/messages", params=find_args
                    )
                    new_paged_messages = assert_good_response(response)
                    paged_messages += new_paged_messages
                    assert len(new_paged_messages) == min(limit, num_remaining)
                    find_args["offset"] = find_args.get("offset", 0) + len(
                        new_paged_messages
                    )

                # Run one more find that should return no messages
                response = await client.get(
                    "/narrativelog/messages", params=find_args
                )
                no_more_paged_messages = assert_good_response(response)
                assert len(no_more_paged_messages) == 0

                assert len(messages) == len(paged_messages)

                # Compare paged to unpaged messages
                for message1, message2 in zip(messages, paged_messages):
                    assert_messages_equal(message1, message2)

            # Check order_by two fields
            for field1, field2 in itertools.product(fields, fields):
                order_by = [field1, field2]
                find_args = {"order_by": order_by}
                response = await client.get(
                    "/narrativelog/messages", params=find_args
                )
                messages = assert_good_response(response)
                if field1 not in str_fields and field2 not in str_fields:
                    assert_messages_ordered(
                        messages=messages, order_by=order_by
                    )

            # Check invalid order_by fields
            for bad_order_by in ("not_a_field", "+id"):
                find_args = {"order_by": [bad_order_by]}
                response = await client.get(
                    "/narrativelog/messages", params=find_args
                )
                assert response.status_code == http.HTTPStatus.BAD_REQUEST

            # Check that limit must be positive
            response = await client.get(
                "/narrativelog/messages", params={"limit": 0}
            )
            assert response.status_code == 422

            # Check that offset must be >= 0
            response = await client.get(
                "/narrativelog/messages", params={"offset": -1}
            )
            assert response.status_code == 422

from __future__ import annotations

import http
import random
import unittest

import httpx

from narrativelog.testutils import (
    TEST_TAGS,
    TEST_URLS,
    MessageDictT,
    assert_good_response,
    cast_special,
    create_test_client,
)


def assert_good_add_response(
    response: httpx.Response, add_args: dict
) -> MessageDictT:
    """Check the response from a successful add_messages request.

    Parameters
    ----------
    response
        Response to HTTP request.
    add_args:
        Arguments to add_message.

    Returns
    -------
    message
        The message added.
    """
    message = assert_good_response(response)
    assert message["is_valid"]
    assert message["parent_id"] is None
    assert message["date_invalidated"] is None
    for key, value in add_args.items():
        assert cast_special(message[key]) == cast_special(add_args[key])
    return message


class AddMessageTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_add_message(self) -> None:
        async with create_test_client(num_messages=0) as (
            client,
            messages,
        ):
            # Add a message with only the required fields specified.
            add_args = dict(
                message_text="A sample message",
                level=10,
                user_id="test_add_message",
                user_agent="pytest",
                is_human=False,
            )
            for suffix in ("", "/"):
                response = await client.post(
                    "/narrativelog/messages" + suffix, json=add_args
                )
                assert_good_add_response(response=response, add_args=add_args)

            # Add a message with all data specified
            # and with all test tags and URLs in random order.
            shuffled_test_tags = TEST_TAGS[:]
            random.shuffle(shuffled_test_tags)
            shuffled_test_urls = TEST_URLS[:]
            random.shuffle(shuffled_test_urls)
            add_args_full = add_args.copy()
            add_args_full["tags"] = shuffled_test_tags
            add_args_full["urls"] = shuffled_test_urls
            add_args_full["time_lost"] = 1234  # seconds
            add_args_full["date_user_specified"] = "2020-01-04T16:41:24"
            response = await client.post(
                "/narrativelog/messages", json=add_args_full
            )
            assert_good_add_response(response=response, add_args=add_args_full)

            # Error: add a message with invalid tags.
            invalid_tags = [
                "not valid",
                "also=not=valid",
                "again?",
            ]
            for num_invalid_tags in range(1, len(invalid_tags)):
                for num_valid_tags in range(2):
                    some_valid_tags = random.sample(TEST_TAGS, num_valid_tags)
                    some_invalid_tags = random.sample(
                        invalid_tags, num_invalid_tags
                    )
                    tags_list = some_valid_tags + some_invalid_tags
                    random.shuffle(tags_list)
                    bad_tags_args = add_args.copy()
                    bad_tags_args["tags"] = tags_list
                    response = await client.post(
                        "/narrativelog/messages",
                        json=bad_tags_args,
                    )
                    assert response.status_code == http.HTTPStatus.BAD_REQUEST

            # Error: add a message that is missing a required field.
            # This is a schema violation so the error code is 422,
            # but I have not found that documented so
            # accept anything in the 400s
            optional_fields = frozenset(
                ["tags", "urls", "time_lost", "date_user_specified"]
            )
            for key in add_args:
                if key in optional_fields:
                    continue
                bad_add_args = add_args.copy()
                del bad_add_args[key]
                response = await client.post(
                    "/narrativelog/messages", json=bad_add_args
                )
                assert 400 <= response.status_code < 500

import http
import random
import unittest
import uuid

import httpx

from narrativelog.testutils import (
    TEST_TAGS,
    ArgDictT,
    MessageDictT,
    assert_good_response,
    create_test_client,
)

random.seed(10)


def assert_good_edit_response(
    response: httpx.Response,
    *,
    old_message: MessageDictT,
    edit_args: ArgDictT,
) -> MessageDictT:
    """Assert that edit messages succeeded and return the new message."""
    new_message = assert_good_response(response)
    assert str(new_message["parent_id"]) == str(old_message["id"])
    assert new_message["is_valid"]
    assert not old_message["is_valid"]
    assert new_message["date_invalidated"] is None
    assert old_message["date_invalidated"] is not None
    for key in old_message:
        if key in set(
            (
                "id",
                "site_id",
                "is_valid",
                "parent_id",
                "date_added",
                "is_valid",
                "date_invalidated",
            )
        ):
            # These are handled above, except date_added,
            # which should not match.
            continue
        elif key in edit_args:
            assert new_message[key] == edit_args[key]
        else:
            assert new_message[key] == old_message[key]
    return new_message


class EditMessageTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_edit_message(self) -> None:
        async with create_test_client(num_messages=1) as (
            client,
            messages,
        ):
            old_id = messages[0]["id"]
            get_old_response = await client.get(
                f"/narrativelog/messages/{old_id}",
            )
            assert_good_response(get_old_response)

            new_tags_list = TEST_TAGS[:]
            random.shuffle(TEST_TAGS)
            full_edit_args = dict(
                site_id="NewSite",
                message_text="New message text",
                level=101,
                tags=new_tags_list,
                urls=["http:://new/url1", "http:://new/url2"],
                user_id="new user_id",
                user_agent="new user_agent",
                is_human=True,
            )
            # Repeatedly edit the old message. Each time
            # add a new version of the message with one field omitted,
            # to check that the one field is not changed from the original.
            # After each edit, find the old message and check that
            # the date_invalidated has been suitably updated.
            for del_key in full_edit_args:
                edit_args = full_edit_args.copy()
                del edit_args[del_key]
                edit_response = await client.patch(
                    f"/narrativelog/messages/{old_id}", json=edit_args
                )
                assert_good_response(edit_response)
                get_old_response = await client.get(
                    f"/narrativelog/messages/{old_id}",
                )
                old_message = assert_good_response(get_old_response)
                assert_good_edit_response(
                    edit_response,
                    old_message=old_message,
                    edit_args=edit_args,
                )

            # Error: edit a message that does not exist.
            edit_args = full_edit_args.copy()
            bad_id = uuid.uuid4()
            response = await client.patch(
                f"/narrativelog/messages/{bad_id}", json=edit_args
            )
            assert response.status_code == http.HTTPStatus.NOT_FOUND

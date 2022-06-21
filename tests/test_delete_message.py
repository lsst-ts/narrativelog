import http
import unittest
import uuid

from narrativelog.testutils import (
    assert_good_response,
    assert_messages_equal,
    create_test_client,
)


class DeleteMessageTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_delete_message(self) -> None:
        async with create_test_client(num_messages=5) as (
            client,
            messages,
        ):
            message_to_delete = messages[2]
            assert message_to_delete["date_invalidated"] is None
            id = message_to_delete["id"]

            # Delete the message
            response = await client.delete(f"/narrativelog/messages/{id}")
            assert response.status_code == http.HTTPStatus.NO_CONTENT

            response = await client.get(f"/narrativelog/messages/{id}")
            deleted_message1 = assert_good_response(response)
            assert not deleted_message1["is_valid"]
            assert deleted_message1["date_invalidated"] is not None

            # Delete the same messages again. This should have no effect.
            response = await client.delete(f"/narrativelog/messages/{id}")
            assert response.status_code == http.HTTPStatus.NO_CONTENT

            response = await client.get(f"/narrativelog/messages/{id}")
            deleted_message2 = assert_good_response(response)
            assert_messages_equal(deleted_message1, deleted_message2)

            # Test that a non-existent message returns NOT_FOUND
            bad_id = uuid.uuid4()
            response = await client.delete(f"/narrativelog/messages/{bad_id}")
            assert response.status_code == http.HTTPStatus.NOT_FOUND

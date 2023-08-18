import http
import unittest
import uuid

from narrativelog.testutils import (
    assert_good_response,
    assert_messages_equal,
    create_test_client,
)


class GetMessageTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_get_message(self) -> None:
        async with create_test_client(num_messages=5) as (
            client,
            messages,
        ):
            chosen_message = messages[2]
            id = chosen_message["id"]
            response = await client.get(f"/narrativelog/messages/{id}")
            message = assert_good_response(response)
            assert_messages_equal(message, chosen_message)

            # Test that a non-existent message returns NOT_FOUND
            bad_id = uuid.uuid4()
            response = await client.get(f"/narrativelog/messages/{bad_id}")
            assert response.status_code == http.HTTPStatus.NOT_FOUND

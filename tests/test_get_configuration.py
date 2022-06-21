import unittest

from narrativelog.shared_state import get_shared_state
from narrativelog.testutils import assert_good_response, create_test_client


class GetRootTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_get_root(self) -> None:
        async with create_test_client(num_messages=0) as (
            client,
            messages,
        ):
            shared_state = get_shared_state()
            for suffix in ("", "/"):
                response = await client.get(
                    "/narrativelog/configuration" + suffix
                )
                data = assert_good_response(response)
                assert data["site_id"] == shared_state.site_id

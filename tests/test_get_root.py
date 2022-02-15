from __future__ import annotations

import http
import unittest

from narrativelog.testutils import create_test_client


class GetRootTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_get_root(self) -> None:
        async with create_test_client(num_messages=0) as (client, messages):
            response = await client.get("/narrativelog/")
            assert response.status_code == http.HTTPStatus.OK
            assert "Narrative log" in response.text
            assert "/narrativelog/docs" in response.text
            assert "OpenAPI" in response.text

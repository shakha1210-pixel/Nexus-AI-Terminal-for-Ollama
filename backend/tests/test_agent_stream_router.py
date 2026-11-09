import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.routers.agents import AgentRunRequest, run_agent


class AgentStreamRouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_unexpected_stream_failure_emits_safe_error_event(self) -> None:
        async def broken_stream(**kwargs):
            yield 'event: status\\ndata: {"message":"started"}\\n\\n'
            raise RuntimeError("private internal detail")

        with patch("app.routers.agents.agent_runtime_service.run", side_effect=broken_stream):
            response = await run_agent("agent-1", AgentRunRequest(model="test", task="hello"))
            chunks = [chunk async for chunk in response.body_iterator]

        payload = "".join(chunk.decode() if isinstance(chunk, bytes) else chunk for chunk in chunks)
        self.assertIn("event: error", payload)
        self.assertIn("Agent oqimida kutilmagan xatolik yuz berdi.", payload)
        self.assertNotIn("private internal detail", payload)

    async def test_unexpected_start_failure_returns_safe_http_error(self) -> None:
        async def broken_start(**kwargs):
            raise RuntimeError("private internal detail")
            yield ""

        with patch("app.routers.agents.agent_runtime_service.run", side_effect=broken_start):
            with self.assertRaises(HTTPException) as raised:
                await run_agent("agent-1", AgentRunRequest(model="test", task="hello"))

        self.assertEqual(raised.exception.status_code, 500)
        self.assertEqual(
            raised.exception.detail,
            "Agent ishga tushmadi. Kutilmagan server xatoligi yuz berdi.",
        )


if __name__ == "__main__":
    unittest.main()

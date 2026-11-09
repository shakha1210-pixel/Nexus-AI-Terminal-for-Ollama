import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.providers.base import BaseAdapter, ProviderCapabilities, ProviderModel
from app.providers.manager import ProviderManager
from app.services.chat_service import ChatService


class FakeAdapter(BaseAdapter):
    provider_id = "fake-provider"

    async def health_check(self):
        return True

    async def list_models(self):
        return [ProviderModel("fake-model", capabilities=ProviderCapabilities(streaming=True))]

    async def chat(self, messages, model, **kwargs):
        return {"message": {"role": "assistant", "content": "unused"}}

    async def stream(self, messages, model, **kwargs):
        yield {"message": {"content": "provider-routed answer"}, "done": False}
        yield {"done": True}


class CancelledFakeAdapter(FakeAdapter):
    async def stream(self, messages, model, **kwargs):
        yield {"message": {"content": "partial answer"}, "done": False}
        raise asyncio.CancelledError()


class ChatProviderRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancelled_stream_persists_partial_assistant_response(self):
        manager = ProviderManager()
        manager.register(CancelledFakeAdapter())
        with tempfile.TemporaryDirectory() as directory:
            service = ChatService(Path(directory))
            with patch("app.services.chat_service.provider_manager", manager):
                emitted = []
                with self.assertRaises(asyncio.CancelledError):
                    async for event in service.stream_chat(
                        model="fake-model", message="hello", conversation_id=None,
                        agent_id="default", paths=[], provider_id="fake-provider",
                    ):
                        emitted.append(event)

            meta = next(event for event in emitted if event.startswith("event: meta"))
            conversation_id = json.loads(meta.split("data: ", 1)[1])["conversation_id"]
            conversation = service.get_conversation(conversation_id)

        self.assertEqual(conversation["messages"][-1], {"role": "assistant", "content": "partial answer"})

    async def test_chat_uses_selected_provider_adapter_stream(self):
        manager = ProviderManager()
        manager.register(FakeAdapter())
        with tempfile.TemporaryDirectory() as directory:
            service = ChatService(Path(directory))
            with patch("app.services.chat_service.provider_manager", manager):
                events = [event async for event in service.stream_chat(
                    model="fake-model", message="hello", conversation_id=None,
                    agent_id="default", paths=[], provider_id="fake-provider",
                )]
        self.assertTrue(any('"content": "provider-routed answer"' in event for event in events))
        self.assertTrue(any("event: done" in event for event in events))


if __name__ == "__main__":
    unittest.main()

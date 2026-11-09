import unittest
from unittest.mock import patch

from app.providers.base import BaseAdapter, ProviderCapabilities, ProviderModel
from app.providers.manager import ProviderManager
from app.services.agent_runtime_service import AgentRuntimeService


class FakeAgentAdapter(BaseAdapter):
    provider_id = "fake-provider"

    async def health_check(self):
        return True

    async def list_models(self):
        return [ProviderModel("agent-model", capabilities=ProviderCapabilities(tool_calling=True))]

    async def chat(self, messages, model, **kwargs):
        return {"message": {"role": "assistant", "content": "agent-routed answer"}}

    async def stream(self, messages, model, **kwargs):
        if False:
            yield {}


class FakeControl:
    def get(self, agent_id):
        return {"isolated": False, "mode": "read_only"}

    def register_request(self, agent_id, task):
        return None

    def unregister_request(self, agent_id, task):
        return None

    def isolate(self, agent_id, reason):
        return {"isolated": True}


class AgentProviderRoutingTests(unittest.IsolatedAsyncioTestCase):
    async def test_agent_uses_same_provider_manager_contract(self):
        manager = ProviderManager()
        manager.register(FakeAgentAdapter())
        service = AgentRuntimeService()
        with patch("app.services.agent_runtime_service.provider_manager", manager):
            with patch("app.services.agent_runtime_service.agent_control_service", FakeControl()):
                events = [event async for event in service.run(
                    agent_id="default", model="agent-model", task="summarize",
                    provider_id="fake-provider",
                )]
        self.assertTrue(any('"content": "agent-routed answer"' in event for event in events))
        self.assertTrue(any("event: done" in event for event in events))


if __name__ == "__main__":
    unittest.main()

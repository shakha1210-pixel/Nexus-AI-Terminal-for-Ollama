import asyncio
import tempfile
import unittest
from pathlib import Path

from app.services.agent_control_service import AgentControlService


class AgentControlServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.control = AgentControlService(Path(self.temp_dir.name))

    def test_list_agent_ids_includes_default_and_configured_agents(self) -> None:
        self.control.set_mode("agent-a", "approval_required")
        self.assertEqual(self.control.list_agent_ids(), ["agent-a", "default"])

    def test_default_is_read_only_and_not_isolated(self) -> None:
        state = self.control.get("agent-a")
        self.assertEqual(state["mode"], "read_only")
        self.assertFalse(state["isolated"])

    def test_modes_and_isolation_release(self) -> None:
        self.assertEqual(self.control.set_mode("agent-a", "autopilot")["mode"], "autopilot")
        locked = self.control.set_mode("agent-a", "locked")
        self.assertTrue(locked["isolated"])
        released = self.control.release("agent-a")
        self.assertFalse(released["isolated"])
        self.assertEqual(released["mode"], "read_only")

    def test_isolation_cancels_active_request(self) -> None:
        async def scenario() -> bool:
            task = asyncio.create_task(asyncio.sleep(30))
            self.control.register_request("agent-a", task)
            self.control.isolate("agent-a", "policy violation")
            try:
                await task
            except asyncio.CancelledError:
                return True
            return False
        self.assertTrue(asyncio.run(scenario()))


if __name__ == "__main__":
    unittest.main()

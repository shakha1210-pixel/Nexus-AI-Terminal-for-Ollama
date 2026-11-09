import unittest

from app.services.agent_runtime_service import AgentRuntimeError, AgentRuntimeService


class AgentRuntimeServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = AgentRuntimeService()

    def test_agent_id_validation(self) -> None:
        self.assertEqual(self.service._validate_agent("agent-01"), "agent-01")
        with self.assertRaises(AgentRuntimeError):
            self.service._validate_agent("../outside")

    def test_runtime_exposes_only_read_file_tool(self) -> None:
        functions = [
            item["function"]["name"]
            for item in self.service.TOOL_DEFINITION
            if item.get("type") == "function"
        ]
        self.assertEqual(functions, ["workspace_read_file"])
        self.assertNotIn("terminal", functions)
        self.assertNotIn("workspace_write_file", functions)

    def test_edit_proposal_tool_is_only_available_in_approval_mode(self) -> None:
        read_tools = self.service.tools_for_mode("read_only")
        approval_tools = self.service.tools_for_mode("approval_required")
        self.assertEqual([item["function"]["name"] for item in read_tools], ["workspace_read_file"])
        self.assertEqual(
            [item["function"]["name"] for item in approval_tools],
            ["workspace_read_file", "workspace_propose_file_edit"],
        )


if __name__ == "__main__":
    unittest.main()

import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.agent_sandbox_service import AgentSandboxError, AgentSandboxService


class AgentSandboxServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = AgentSandboxService()

    def test_command_is_networkless_read_only_and_resource_limited(self) -> None:
        command = self.service._command(Path("/tmp/nexus-input.txt"), "nexus-agent-read-test")
        joined = " ".join(command)
        for required in (
            "--network=none", "--read-only", "--cap-drop=ALL", "--name nexus-agent-read-test",
            "--security-opt=no-new-privileges", "--pids-limit=16",
            "--memory=96m", "--cpus=0.50", "--user=65532:65532",
            "readonly", "nexus-agent-sandbox:py311",
        ):
            self.assertIn(required, joined)
        self.assertNotIn("--privileged", command)
        self.assertNotIn("/var/run/docker.sock", joined)

    def test_rejects_unsafe_paths(self) -> None:
        for path in ("../secret", "/etc/passwd", "C:/Windows/win.ini", "folder\\file", "a//b"):
            with self.subTest(path=path), self.assertRaises(AgentSandboxError):
                self.service._validate_relative_path(path)

    def test_rejects_comma_in_mount_source(self) -> None:
        with self.assertRaises(AgentSandboxError):
            self.service._command(Path("/tmp/a,b.txt"), "nexus-agent-read-test")

    def test_ungranted_path_fails_before_docker(self) -> None:
        with patch(
            "app.services.agent_sandbox_service.agent_access_service.list_permissions",
            return_value={"permissions": []},
        ), patch("app.services.agent_sandbox_service.asyncio.create_subprocess_exec") as spawn:
            with self.assertRaises(AgentSandboxError):
                asyncio.run(self.service.read_granted_file("agent-a", "notes.md"))
            spawn.assert_not_called()


if __name__ == "__main__":
    unittest.main()

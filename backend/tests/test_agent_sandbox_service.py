import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from app.services.agent_sandbox_service import AgentSandboxError, AgentSandboxService


class AgentSandboxServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = AgentSandboxService()

    def test_command_is_networkless_read_only_and_resource_limited(self) -> None:
        command = self.service._command(Path("/tmp/nexus-input.txt"), "nexus-agent-read-test")
        joined = " ".join(command)
        for required in (
            "--network=none", "--read-only", "--cap-drop=ALL",
            "--security-opt=no-new-privileges", "--pids-limit=16",
            "--memory=96m", "--memory-swap=96m", "--cpus=0.50",
            "--user=65532:65532", "--name nexus-agent-read-test", "readonly",
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

    def test_stage_rejects_non_utf8_files(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "binary.txt"
            path.write_bytes(bytes([255]))
            with patch(
                "app.services.agent_sandbox_service.agent_access_service.list_permissions",
                return_value={"permissions": [{"path": "binary.txt"}]},
            ), patch(
                "app.services.agent_sandbox_service.workspace_service.resolve",
                return_value=path,
            ):
                with self.assertRaises(AgentSandboxError):
                    self.service._stage_granted_file("agent-a", "binary.txt")

    def test_stage_rejects_files_over_2mb(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "large.txt"
            path.write_bytes(b"x" * (self.service.MAX_FILE_BYTES + 1))
            with patch(
                "app.services.agent_sandbox_service.agent_access_service.list_permissions",
                return_value={"permissions": [{"path": "large.txt"}]},
            ), patch(
                "app.services.agent_sandbox_service.workspace_service.resolve",
                return_value=path,
            ):
                with self.assertRaisesRegex(AgentSandboxError, "2 MB"):
                    self.service._stage_granted_file("agent-a", "large.txt")

    def test_timeout_kills_process_removes_container_and_staged_file(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as staged:
            staged_path = staged.name
        process = SimpleNamespace(
            returncode=None,
            kill=Mock(),
            communicate=AsyncMock(return_value=(b"", b"")),
        )
        async def scenario() -> None:
            with patch.object(self.service, "_stage_granted_file", return_value=staged_path), \\
                 patch("app.services.agent_sandbox_service.asyncio.create_subprocess_exec", new=AsyncMock(return_value=process)), \\
                 patch("app.services.agent_sandbox_service.asyncio.wait_for", new=AsyncMock(side_effect=asyncio.TimeoutError)), \\
                 patch.object(self.service, "_force_remove", new=AsyncMock()) as remove:
                with self.assertRaisesRegex(AgentSandboxError, "vaqt limiti"):
                    await self.service.read_granted_file("agent-a", "notes.md")
                process.kill.assert_called_once()
                remove.assert_awaited_once()
                self.assertFalse(Path(staged_path).exists())
        asyncio.run(scenario())

    def test_cancellation_kills_process_removes_container_and_staged_file(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as staged:
            staged_path = staged.name
        process = SimpleNamespace(
            returncode=None,
            kill=Mock(),
            communicate=AsyncMock(side_effect=[asyncio.CancelledError(), (b"", b"")]),
        )
        async def scenario() -> None:
            with patch.object(self.service, "_stage_granted_file", return_value=staged_path), \\
                 patch("app.services.agent_sandbox_service.asyncio.create_subprocess_exec", new=AsyncMock(return_value=process)), \\
                 patch.object(self.service, "_force_remove", new=AsyncMock()) as remove:
                with self.assertRaises(asyncio.CancelledError):
                    await self.service.read_granted_file("agent-a", "notes.md")
                process.kill.assert_called_once()
                remove.assert_awaited_once()
                self.assertFalse(Path(staged_path).exists())
        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()

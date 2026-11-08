import base64
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.agent_access_service import AgentAccessError
from app.services.agent_sandbox_service import AgentSandboxError, AgentSandboxService


class AgentSandboxServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.service = AgentSandboxService(
            storage_root=Path(self.temp_dir.name) / "sandboxes",
            docker_binary="docker-test",
            image="python:test",
        )

    def _context(self, agent_id: str, paths: list[str]) -> dict:
        return {
            "agent_id": agent_id,
            "attachments": [
                {"path": "docs/brief.txt", "kind": "text", "content": "private note"},
                {
                    "path": "images/picture.png",
                    "kind": "image",
                    "content_base64": base64.b64encode(b"image-data").decode("ascii"),
                },
            ],
        }

    def test_start_uses_hardened_networkless_container_and_only_granted_snapshot(self) -> None:
        calls: list[list[str]] = []

        def docker(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
            calls.append(args)
            return subprocess.CompletedProcess(["docker-test", *args], 0, "container-id\n", "")

        with patch.object(self.service, "_container_status", return_value="absent"):
            with patch.object(self.service, "_docker", side_effect=docker):
                with patch("app.services.agent_sandbox_service.agent_access_service.build_context", side_effect=self._context):
                    result = self.service.start("agent-a", ["docs/brief.txt", "images/picture.png"])

        self.assertEqual(result["status"], "running")
        run_args = calls[-1]
        self.assertIn("--network", run_args)
        self.assertEqual(run_args[run_args.index("--network") + 1], "none")
        self.assertIn("--read-only", run_args)
        self.assertIn("--cap-drop", run_args)
        self.assertEqual(run_args[run_args.index("--cap-drop") + 1], "ALL")
        self.assertIn("--pids-limit", run_args)
        self.assertIn("--memory", run_args)
        self.assertIn("--cpus", run_args)
        self.assertIn("--security-opt", run_args)
        self.assertIn("--pull=never", run_args)
        self.assertNotIn("/var/run/docker.sock", " ".join(run_args))

        stage = self.service._stage_path("agent-a")
        self.assertEqual((stage / "docs" / "brief.txt").read_text(), "private note")
        self.assertEqual((stage / "images" / "picture.png").read_bytes(), b"image-data")
        self.assertEqual((stage / "docs" / "brief.txt").stat().st_mode & 0o777, 0o444)
        self.assertEqual(stage.stat().st_mode & 0o777, 0o555)

    def test_start_fails_closed_when_docker_cli_is_missing(self) -> None:
        with patch("app.services.agent_sandbox_service.subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaisesRegex(AgentSandboxError, "Docker CLI topilmadi"):
                self.service.start("agent-a", ["docs/brief.txt"])

    def test_start_rejects_ungranted_files(self) -> None:
        with patch.object(self.service, "_container_status", return_value="absent"):
            with patch.object(self.service, "_docker", return_value=subprocess.CompletedProcess([], 0, "", "")):
                with patch(
                "app.services.agent_sandbox_service.agent_access_service.build_context",
                side_effect=AgentAccessError("read grant missing"),
            ):
                    with self.assertRaisesRegex(AgentSandboxError, "read grant missing"):
                        self.service.start("agent-a", ["secret.txt"])

    def test_stop_removes_container_and_read_only_snapshot(self) -> None:
        stage = self.service._stage_path("agent-a")
        stage.mkdir(parents=True)
        nested = stage / "nested"
        nested.mkdir()
        (nested / "file.txt").write_text("data")
        (nested / "file.txt").chmod(0o444)
        nested.chmod(0o555)
        stage.chmod(0o555)

        with patch.object(self.service, "_container_status", return_value="running"):
            with patch.object(self.service, "_docker", return_value=subprocess.CompletedProcess([], 0, "", "")) as docker:
                result = self.service.stop("agent-a")

        self.assertEqual(result["status"], "stopped")
        self.assertFalse(stage.exists())
        self.assertEqual(docker.call_args_list[0].args[0], ["info", "--format", "{{.ServerVersion}}"])
        self.assertEqual(docker.call_args_list[1].args[0], ["rm", "--force", self.service._name("agent-a")])

    def test_status_reports_unavailable_docker(self) -> None:
        with patch.object(self.service, "_ensure_docker", side_effect=AgentSandboxError("Docker unavailable")):
            result = self.service.status("agent-a")
        self.assertFalse(result["available"])
        self.assertEqual(result["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()

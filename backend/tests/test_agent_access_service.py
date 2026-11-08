import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import os

from app.services.agent_access_service import AgentAccessError, AgentAccessService
from app.services.workspace_service import WorkspaceService


class AgentAccessServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name) / "workspace"
        with patch.dict(os.environ, {"NEXUS_WORKSPACE_ROOT": str(self.root)}):
            self.workspace = WorkspaceService()
        self.service = AgentAccessService(Path(self.temp_dir.name) / "permissions.json")
        self.workspace.create_file("notes.md", "private project notes")
        self.original_workspace = __import__("app.services.agent_access_service", fromlist=["workspace_service"]).workspace_service
        import app.services.agent_access_service as access_module
        self._module = access_module
        self._module.workspace_service = self.workspace
        self.addCleanup(setattr, self._module, "workspace_service", self.original_workspace)

    def test_context_requires_explicit_read_grant(self) -> None:
        with self.assertRaises(AgentAccessError):
            self.service.build_context("writer", ["notes.md"])
        self.service.grant_read("writer", "notes.md")
        result = self.service.build_context("writer", ["notes.md"])
        self.assertEqual(result["attachments"][0]["content"], "private project notes")

    def test_revoking_grant_blocks_context(self) -> None:
        self.service.grant_read("writer", "notes.md")
        self.service.revoke_read("writer", "notes.md")
        with self.assertRaises(AgentAccessError):
            self.service.build_context("writer", ["notes.md"])

    def test_image_context_is_base64_and_scoped(self) -> None:
        image = self.root / "pixel.png"
        image.write_bytes(b"fake-image")
        self.service.grant_read("vision", "pixel.png")
        result = self.service.build_context("vision", ["pixel.png"])
        self.assertEqual(result["attachments"][0]["kind"], "image")
        self.assertEqual(base64.b64decode(result["attachments"][0]["content_base64"]), b"fake-image")

    def test_rejects_invalid_agent_id_and_ungranted_path(self) -> None:
        with self.assertRaises(AgentAccessError):
            self.service.list_permissions("../host")
        self.service.grant_read("agent-a", "notes.md")
        with self.assertRaises(AgentAccessError):
            self.service.build_context("agent-a", ["../outside.txt"])


if __name__ == "__main__":
    unittest.main()

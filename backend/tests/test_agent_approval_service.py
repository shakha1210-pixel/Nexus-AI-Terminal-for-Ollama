import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import os

from app.services.agent_approval_service import AgentApprovalError, AgentApprovalService
from app.services.workspace_service import WorkspaceService


class AgentApprovalServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name) / "workspace"
        with patch.dict(os.environ, {"NEXUS_WORKSPACE_ROOT": str(self.root)}):
            self.workspace = WorkspaceService()
        self.workspace.create_file("notes.md", "original")
        self.original_workspace = __import__(
            "app.services.agent_approval_service", fromlist=["workspace_service"]
        ).workspace_service
        import app.services.agent_approval_service as approval_module
        self.module = approval_module
        self.module.workspace_service = self.workspace
        self.addCleanup(setattr, self.module, "workspace_service", self.original_workspace)
        self.service = AgentApprovalService(Path(self.temp_dir.name) / "approvals.json")
        self.mode_patch = patch(
            "app.services.agent_approval_service.agent_control_service.get",
            return_value={"mode": "approval_required", "isolated": False},
        )
        self.mode_patch.start()
        self.addCleanup(self.mode_patch.stop)

    def test_create_does_not_write_until_approved(self) -> None:
        request = self.service.create_request("agent-a", "notes.md", "proposed")
        self.assertEqual(self.workspace.read_file("notes.md")["content"], "original")
        self.assertEqual(request["status"], "pending")
        self.assertEqual(request["original_content"], "original")
        self.assertEqual(request["proposed_content"], "proposed")
        result = self.service.decide("agent-a", request["request_id"], True)
        self.assertEqual(result["status"], "approved")
        self.assertEqual(self.workspace.read_file("notes.md")["content"], "proposed")

    def test_legacy_pending_request_without_snapshot_remains_listable(self) -> None:
        request_id = "a" * 32
        legacy_item = {
            "request_id": request_id,
            "agent_id": "agent-a",
            "path": "notes.md",
            "operation": "replace_file",
            "proposed_content": "proposed",
            "original_sha256": "legacy-hash",
            "proposed_sha256": "proposed-hash",
            "status": "pending",
            "created_at": "2026-01-01T00:00:00+00:00",
            "expires_at": "2999-01-01T00:00:00+00:00",
        }
        self.service.store_path.write_text(json.dumps({request_id: legacy_item}), encoding="utf-8")

        result = self.service.list_requests("agent-a")

        self.assertEqual(len(result["requests"]), 1)
        self.assertIsNone(result["requests"][0]["original_content"])
        self.assertEqual(result["requests"][0]["proposed_content"], "proposed")

    def test_rejection_is_final(self) -> None:
        request = self.service.create_request("agent-a", "notes.md", "proposed")
        result = self.service.decide("agent-a", request["request_id"], False)
        self.assertEqual(result["status"], "rejected")
        with self.assertRaises(AgentApprovalError):
            self.service.decide("agent-a", request["request_id"], True)
        self.assertEqual(self.workspace.read_file("notes.md")["content"], "original")

    def test_stale_file_cannot_be_overwritten(self) -> None:
        request = self.service.create_request("agent-a", "notes.md", "proposed")
        self.workspace.write_file("notes.md", "changed by user")
        with self.assertRaises(AgentApprovalError):
            self.service.decide("agent-a", request["request_id"], True)
        self.assertEqual(self.workspace.read_file("notes.md")["content"], "changed by user")

    def test_requires_approval_mode_and_existing_text_file(self) -> None:
        with patch(
            "app.services.agent_approval_service.agent_control_service.get",
            return_value={"mode": "read_only", "isolated": False},
        ), self.assertRaises(AgentApprovalError):
            self.service.create_request("agent-a", "notes.md", "x")
        with self.assertRaises(AgentApprovalError):
            self.service.create_request("agent-a", "../outside", "x")
        with self.assertRaises(AgentApprovalError):
            self.service.create_request("agent-a", "new.md", "x")

    def test_request_is_scoped_to_agent(self) -> None:
        request = self.service.create_request("agent-a", "notes.md", "proposed")
        with self.assertRaises(AgentApprovalError):
            self.service.decide("agent-b", request["request_id"], True)

    def test_expired_request_cannot_be_approved(self) -> None:
        request = self.service.create_request("agent-a", "notes.md", "proposed")
        stored = json.loads(self.service.store_path.read_text(encoding="utf-8"))
        stored[request["request_id"]]["expires_at"] = "2000-01-01T00:00:00+00:00"
        self.service.store_path.write_text(json.dumps(stored), encoding="utf-8")
        with self.assertRaises(AgentApprovalError):
            self.service.decide("agent-a", request["request_id"], True)
        self.assertEqual(self.workspace.read_file("notes.md")["content"], "original")

    def test_symlink_target_is_rejected(self) -> None:
        outside = Path(self.temp_dir.name) / "outside.md"
        outside.write_text("outside", encoding="utf-8")
        link = self.root / "linked.md"
        link.symlink_to(outside)
        with self.assertRaises(AgentApprovalError):
            self.service.create_request("agent-a", "linked.md", "replacement")
        self.assertEqual(outside.read_text(encoding="utf-8"), "outside")


if __name__ == "__main__":
    unittest.main()

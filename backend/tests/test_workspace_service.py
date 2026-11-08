import base64
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.workspace_service import WorkspaceError, WorkspaceService


class WorkspaceServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name) / "workspace"
        with patch.dict(os.environ, {"NEXUS_WORKSPACE_ROOT": str(self.root)}):
            self.service = WorkspaceService()

    def test_create_and_read_text_file(self) -> None:
        created = self.service.create_file("src/main.py", "print('NEXUS')")
        self.assertEqual(created["path"], "src/main.py")
        self.assertEqual(self.service.read_file("src/main.py")["content"], "print('NEXUS')")

    def test_rejects_path_traversal(self) -> None:
        with self.assertRaises(WorkspaceError):
            self.service.create_file("../outside.txt", "blocked")

    def test_uploads_file_and_lists_it(self) -> None:
        self.service.create_directory("assets")
        payload = base64.b64encode(b"nexus-file").decode("ascii")
        uploaded = self.service.save_upload("assets", "sample.bin", payload)
        self.assertEqual(uploaded["path"], "assets/sample.bin")
        self.assertEqual((self.root / uploaded["path"]).read_bytes(), b"nexus-file")
        names = [entry["name"] for entry in self.service.tree("assets")["entries"]]
        self.assertIn("sample.bin", names)

    def test_does_not_list_symlinks(self) -> None:
        outside = Path(self.temp_dir.name) / "outside"
        outside.mkdir()
        (outside / "secret.txt").write_text("private", encoding="utf-8")
        link = self.root / "external-link"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks are not supported in this environment")
        names = [entry["name"] for entry in self.service.tree()["entries"]]
        self.assertNotIn("external-link", names)
        with self.assertRaises(WorkspaceError):
            self.service.resolve("external-link/secret.txt")


if __name__ == "__main__":
    unittest.main()

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.app_data import get_data_dir, get_store_path


class AppDataTests(unittest.TestCase):
    def test_override_is_respected(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"NEXUS_DATA_DIR": tmp}):
            self.assertEqual(get_data_dir(), Path(tmp))

    def test_legacy_file_migrates_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "legacy.json"
            legacy.write_text('{"theme":"dark"}', encoding="utf-8")
            with patch.dict(os.environ, {"NEXUS_DATA_DIR": str(root / "data")}):
                target = get_store_path("preferences.json", legacy)
                self.assertEqual(target.read_text(encoding="utf-8"), '{"theme":"dark"}')
                target.write_text('{"theme":"light"}', encoding="utf-8")
                self.assertEqual(get_store_path("preferences.json", legacy).read_text(encoding="utf-8"), '{"theme":"light"}')

    def test_missing_legacy_file_is_not_created(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"NEXUS_DATA_DIR": tmp}):
            self.assertFalse(get_store_path("state.json", Path(tmp) / "missing.json").exists())


if __name__ == "__main__":
    unittest.main()

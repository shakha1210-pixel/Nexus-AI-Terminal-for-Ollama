import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services.app_data import get_data_dir, get_store_dir, get_store_path


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

    def test_interrupted_file_migration_leaves_no_partial_destination_and_can_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "legacy.json"
            legacy.write_text('{"complete":true}', encoding="utf-8")
            data_dir = root / "data"
            with patch.dict(os.environ, {"NEXUS_DATA_DIR": str(data_dir)}):
                def interrupted_copy(source, destination):
                    Path(destination).write_text('{"partial":', encoding="utf-8")
                    raise OSError("simulated interruption")

                with patch("app.services.app_data.shutil.copy2", side_effect=interrupted_copy):
                    with self.assertRaises(OSError):
                        get_store_path("preferences.json", legacy)

                target = data_dir / "preferences.json"
                self.assertFalse(target.exists())
                self.assertEqual(list(data_dir.glob("*.migration")), [])

                migrated = get_store_path("preferences.json", legacy)
                self.assertEqual(migrated.read_text(encoding="utf-8"), '{"complete":true}')

    def test_legacy_directory_migrates_once_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "legacy-conversations"
            legacy.mkdir()
            (legacy / "conversation.json").write_text('{"messages":[]}', encoding="utf-8")
            with patch.dict(os.environ, {"NEXUS_DATA_DIR": str(root / "data")}):
                target = get_store_dir("conversations", legacy)
                self.assertEqual((target / "conversation.json").read_text(encoding="utf-8"), '{"messages":[]}')
                (target / "conversation.json").write_text('{"messages":[1]}', encoding="utf-8")
                self.assertEqual(get_store_dir("conversations", legacy).joinpath("conversation.json").read_text(encoding="utf-8"), '{"messages":[1]}')

    def test_existing_store_merges_missing_legacy_files_without_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "legacy-conversations"
            (legacy / "nested").mkdir(parents=True)
            (legacy / "same.json").write_text('{"source":"legacy"}', encoding="utf-8")
            (legacy / "nested" / "older.json").write_text('{"messages":[1]}', encoding="utf-8")
            data = root / "data"
            destination = data / "conversations"
            destination.mkdir(parents=True)
            (destination / "same.json").write_text('{"source":"current"}', encoding="utf-8")
            with patch.dict(os.environ, {"NEXUS_DATA_DIR": str(data)}):
                result = get_store_dir("conversations", legacy)
            self.assertEqual((result / "same.json").read_text(encoding="utf-8"), '{"source":"current"}')
            self.assertEqual((result / "nested" / "older.json").read_text(encoding="utf-8"), '{"messages":[1]}')

    def test_missing_legacy_file_is_not_created(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"NEXUS_DATA_DIR": tmp}):
            self.assertFalse(get_store_path("state.json", Path(tmp) / "missing.json").exists())


if __name__ == "__main__":
    unittest.main()

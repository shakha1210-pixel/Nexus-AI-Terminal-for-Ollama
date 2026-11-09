import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.schemas.preferences import UIPreferences
from app.services.preferences_service import PreferencesService


class PreferencesServiceTests(unittest.TestCase):
    def test_defaults_include_uzbek_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            service = PreferencesService(Path(tmp) / "preferences.json")
            self.assertEqual(service.get(), UIPreferences())

    def test_round_trip_persists_language_and_theme(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "preferences.json"
            service = PreferencesService(path)
            expected = UIPreferences(theme="light", sound_enabled=True, language="en")
            self.assertEqual(service.update(expected), expected)
            self.assertEqual(service.get(), expected)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["language"], "en")

    def test_corrupt_file_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "preferences.json"
            path.write_text("{broken", encoding="utf-8")
            self.assertEqual(PreferencesService(path).get(), UIPreferences())

    def test_legacy_preferences_migrate_on_first_access_not_initialization(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy_dir = root / "legacy"
            legacy_dir.mkdir()
            (legacy_dir / "preferences.json").write_text('{"language":"en"}', encoding="utf-8")
            data_dir = root / "data"
            with (
                patch("app.services.preferences_service._LEGACY_DIR", legacy_dir),
                patch.dict(os.environ, {"NEXUS_DATA_DIR": str(data_dir)}),
            ):
                service = PreferencesService()
                target = data_dir / "preferences.json"
                self.assertFalse(target.exists())
                self.assertEqual(service.get().language, "en")
                self.assertTrue(target.is_file())


if __name__ == "__main__":
    unittest.main()

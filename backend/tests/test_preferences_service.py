import json
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()

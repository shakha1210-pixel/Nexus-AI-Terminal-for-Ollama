import json
import threading
from pathlib import Path

from app.schemas.preferences import UIPreferences

_DATA_DIR = Path(__file__).resolve().parents[2] / ".nexus"
_PREFERENCES_FILE = _DATA_DIR / "preferences.json"


class PreferencesService:
    def __init__(self) -> None:
        self._lock = threading.Lock()

    def get(self) -> UIPreferences:
        with self._lock:
            try:
                payload = json.loads(_PREFERENCES_FILE.read_text(encoding="utf-8"))
                return UIPreferences.model_validate(payload)
            except FileNotFoundError:
                return UIPreferences()
            except (json.JSONDecodeError, ValueError):
                return UIPreferences()

    def update(self, preferences: UIPreferences) -> UIPreferences:
        payload = preferences.model_dump()
        with self._lock:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            temporary = _PREFERENCES_FILE.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            temporary.replace(_PREFERENCES_FILE)
        return preferences


preferences_service = PreferencesService()

import json
import threading
from pathlib import Path

from app.schemas.preferences import UIPreferences
from app.services.app_data import get_store_path

_LEGACY_DIR = Path(__file__).resolve().parents[2] / ".nexus"


class PreferencesService:
    def __init__(self, store_path: Path | None = None) -> None:
        self.store_path = store_path or get_store_path("preferences.json", _LEGACY_DIR / "preferences.json")
        self._lock = threading.Lock()

    def get(self) -> UIPreferences:
        with self._lock:
            try:
                payload = json.loads(self.store_path.read_text(encoding="utf-8"))
                return UIPreferences.model_validate(payload)
            except (FileNotFoundError, json.JSONDecodeError, ValueError):
                return UIPreferences()

    def update(self, preferences: UIPreferences) -> UIPreferences:
        payload = preferences.model_dump(mode="json")
        with self._lock:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.store_path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(self.store_path)
        return preferences


preferences_service = PreferencesService()

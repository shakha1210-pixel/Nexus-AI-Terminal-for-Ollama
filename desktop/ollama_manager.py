from __future__ import annotations

import json
import shutil
import urllib.error
import urllib.request
from dataclasses import dataclass


OLLAMA_URL = "http://127.0.0.1:11434/api/version"


@dataclass(frozen=True)
class OllamaStatus:
    installed: bool
    running: bool
    version: str | None = None
    executable: str | None = None
    message: str = ""


def check_ollama(timeout: float = 1.5) -> OllamaStatus:
    """Detect the Ollama CLI and local API without starting or changing anything."""
    executable = shutil.which("ollama")
    try:
        request = urllib.request.Request(OLLAMA_URL, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        version = payload.get("version") if isinstance(payload, dict) else None
        return OllamaStatus(
            installed=bool(executable),
            running=True,
            version=version if isinstance(version, str) else None,
            executable=executable,
            message="Ollama local API is responding.",
        )
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        if executable:
            message = "Ollama is installed but its local API is not responding. Start Ollama and try again."
        else:
            message = "Ollama was not detected. Install Ollama separately, then launch it before using local models."
        return OllamaStatus(
            installed=bool(executable),
            running=False,
            executable=executable,
            message=message,
        )

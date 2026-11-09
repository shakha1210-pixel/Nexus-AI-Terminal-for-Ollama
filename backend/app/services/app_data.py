import os
import shutil
import sys
from pathlib import Path


def get_data_dir() -> Path:
    """Return the per-user NEXUS data directory."""
    override = os.getenv("NEXUS_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "win32":
        root = os.getenv("LOCALAPPDATA")
        if root:
            return Path(root) / "NEXUS AI"
        return Path.home() / "AppData" / "Local" / "NEXUS AI"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "NEXUS AI"
    root = os.getenv("XDG_DATA_HOME")
    return (Path(root).expanduser() if root else Path.home() / ".local" / "share") / "nexus-ai"


def get_store_path(filename: str, legacy_path: Path | None = None) -> Path:
    """Resolve a store path and migrate a legacy file once without overwriting data."""
    destination = get_data_dir() / filename
    if not destination.exists() and legacy_path is not None and legacy_path.is_file():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(legacy_path, destination)
    return destination

def get_store_dir(dirname: str, legacy_dir: Path | None = None) -> Path:
    """Resolve a per-user data directory and migrate legacy contents once."""
    destination = get_data_dir() / dirname
    if not destination.exists() and legacy_dir is not None and legacy_dir.is_dir():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(legacy_dir, destination)
    return destination

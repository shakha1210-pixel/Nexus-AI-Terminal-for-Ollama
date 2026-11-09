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
    """Resolve a per-user store and copy missing legacy files without overwriting data."""
    destination = get_data_dir() / dirname
    if legacy_dir is None or not legacy_dir.is_dir():
        return destination

    for source_root, directory_names, file_names in os.walk(legacy_dir, followlinks=False):
        source_dir = Path(source_root)
        relative_dir = source_dir.relative_to(legacy_dir)
        safe_directories = [
            name for name in directory_names
            if not (source_dir / name).is_symlink()
        ]
        directory_names[:] = safe_directories
        target_dir = destination / relative_dir
        for name in safe_directories:
            (target_dir / name).mkdir(parents=True, exist_ok=True)
        for name in file_names:
            source_file = source_dir / name
            if source_file.is_symlink() or not source_file.is_file():
                continue
            target_file = target_dir / name
            if target_file.exists():
                continue
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_file, target_file)
    return destination

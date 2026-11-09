from __future__ import annotations

import base64
import os
from pathlib import Path


class WorkspaceError(ValueError):
    pass


class WorkspaceService:
    MAX_READ_BYTES = 2 * 1024 * 1024
    MAX_UPLOAD_BYTES = 10 * 1024 * 1024

    def __init__(self) -> None:
        configured = os.getenv("NEXUS_WORKSPACE_ROOT", str(Path.home() / "NexusWorkspace"))
        self.root = Path(configured).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative_path: str = "") -> Path:
        candidate = (self.root / relative_path).resolve()
        if not candidate.is_relative_to(self.root):
            raise WorkspaceError("Workspace tashqarisiga chiqishga ruxsat yo‘q.")
        if candidate != self.root and not candidate.exists():
            parent = candidate.parent
            if not parent.resolve().is_relative_to(self.root):
                raise WorkspaceError("Noto‘g‘ri fayl yo‘li.")
        return candidate

    def tree(self, relative_path: str = "") -> dict:
        directory = self.resolve(relative_path)
        if not directory.is_dir():
            raise WorkspaceError("Ko‘rsatilgan yo‘l papka emas.")
        entries = []
        for item in sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if item.is_symlink():
                continue
            try:
                resolved = item.resolve()
                if not resolved.is_relative_to(self.root):
                    continue
                stat = item.stat()
            except OSError:
                continue
            entries.append({
                "name": item.name,
                "path": item.relative_to(self.root).as_posix(),
                "kind": "directory" if item.is_dir() else "file",
                "size": stat.st_size if item.is_file() else None,
                "modified_at": stat.st_mtime,
            })
        return {"root_name": self.root.name, "path": relative_path, "entries": entries}

    def read_file(self, relative_path: str) -> dict:
        path = self.resolve(relative_path)
        if not path.is_file() or path.is_symlink():
            raise WorkspaceError("Fayl topilmadi.")
        size = path.stat().st_size
        if size > self.MAX_READ_BYTES:
            raise WorkspaceError("Fayl 2 MB dan katta. Hozircha faqat kichik matnli fayllar ochiladi.")
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise WorkspaceError("Bu fayl matn formatida emas.") from exc
        return {"path": relative_path, "content": content, "size": size}

    def create_file(self, relative_path: str, content: str = "") -> dict:
        if not relative_path:
            raise WorkspaceError("Fayl yo‘li bo‘sh.")
        path = self.resolve(relative_path)
        if path.exists():
            raise WorkspaceError("Bu nomdagi fayl allaqachon mavjud.")
        return self.write_file(relative_path, content)

    def write_file(self, relative_path: str, content: str) -> dict:
        if not relative_path or len(content.encode("utf-8")) > self.MAX_READ_BYTES:
            raise WorkspaceError("Fayl yo‘li bo‘sh yoki matn hajmi 2 MB dan katta.")
        path = self.resolve(relative_path)
        if path == self.root or path.is_dir():
            raise WorkspaceError("Fayl yo‘li noto‘g‘ri.")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.parent.resolve() != self.root and not path.parent.resolve().is_relative_to(self.root):
            raise WorkspaceError("Workspace tashqarisiga yozishga ruxsat yo‘q.")
        path.write_text(content, encoding="utf-8")
        return {"path": relative_path, "size": path.stat().st_size}

    def create_directory(self, relative_path: str) -> dict:
        if not relative_path:
            raise WorkspaceError("Papka nomi kiritilmadi.")
        path = self.resolve(relative_path)
        path.mkdir(parents=True, exist_ok=True)
        return {"path": relative_path, "created": True}

    def save_upload(self, relative_path: str, filename: str, data_base64: str) -> dict:
        safe_name = Path(filename).name
        if not safe_name or safe_name in {".", ".."}:
            raise WorkspaceError("Fayl nomi noto‘g‘ri.")
        try:
            payload = base64.b64decode(data_base64, validate=True)
        except (ValueError, base64.binascii.Error) as exc:
            raise WorkspaceError("Fayl ma’lumoti noto‘g‘ri.") from exc
        if len(payload) > self.MAX_UPLOAD_BYTES:
            raise WorkspaceError("Yuklanadigan fayl 10 MB dan katta bo‘lmasligi kerak.")
        folder = self.resolve(relative_path)
        if not folder.is_dir():
            raise WorkspaceError("Yuklash uchun papka topilmadi.")
        destination = self.resolve((Path(relative_path) / safe_name).as_posix())
        if destination.exists():
            raise WorkspaceError("Bu nomdagi fayl allaqachon mavjud.")
        destination.write_bytes(payload)
        return {"path": destination.relative_to(self.root).as_posix(), "size": len(payload)}


workspace_service = WorkspaceService()

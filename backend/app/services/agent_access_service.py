from __future__ import annotations

import base64
import json
import re
import threading
from pathlib import Path

from app.services.app_data import get_data_dir, get_store_path
from app.services.workspace_service import WorkspaceError, workspace_service


class AgentAccessError(ValueError):
    pass


class AgentAccessService:
    IMAGE_TYPES = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".gif": "image/gif", ".webp": "image/webp",
    }
    MAX_CONTEXT_FILE_BYTES = 10 * 1024 * 1024

    def __init__(self, store_path: Path | None = None) -> None:
        self.store_path = store_path or (get_data_dir() / "agent_permissions.json")
        self._legacy_store_path = (
            Path(__file__).resolve().parents[2] / ".nexus" / "agent_permissions.json"
            if store_path is None else None
        )
        self._lock = threading.RLock()

    @staticmethod
    def _validate_agent_id(agent_id: str) -> str:
        value = agent_id.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value):
            raise AgentAccessError("Agent ID formati noto‘g‘ri.")
        return value

    def _load(self) -> dict[str, list[str]]:
        if self._legacy_store_path is not None and not self.store_path.exists():
            get_store_path(self.store_path.name, self._legacy_store_path)
        try:
            raw = json.loads(self.store_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (json.JSONDecodeError, OSError) as exc:
            raise AgentAccessError("Agent ruxsatlari faylini o‘qib bo‘lmadi.") from exc
        if not isinstance(raw, dict):
            raise AgentAccessError("Agent ruxsatlari ma’lumoti noto‘g‘ri.")
        return {key: value for key, value in raw.items() if isinstance(key, str) and isinstance(value, list)}

    def _save(self, data: dict[str, list[str]]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.store_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.store_path)

    def list_agent_ids(self) -> list[str]:
        with self._lock:
            return sorted(self._load().keys())

    def list_permissions(self, agent_id: str) -> dict:
        agent = self._validate_agent_id(agent_id)
        with self._lock:
            paths = sorted(set(self._load().get(agent, [])))
        return {"agent_id": agent, "permissions": [{"path": path, "access": "read"} for path in paths]}

    def grant_read(self, agent_id: str, relative_path: str) -> dict:
        agent = self._validate_agent_id(agent_id)
        try:
            target = workspace_service.resolve(relative_path)
        except WorkspaceError as exc:
            raise AgentAccessError(str(exc)) from exc
        if target.is_symlink() or not target.is_file():
            raise AgentAccessError("Faqat workspace ichidagi oddiy faylga read ruxsati berish mumkin.")
        with self._lock:
            data = self._load()
            paths = set(data.get(agent, []))
            paths.add(target.relative_to(workspace_service.root).as_posix())
            data[agent] = sorted(paths)
            self._save(data)
        return self.list_permissions(agent)

    def revoke_read(self, agent_id: str, relative_path: str) -> dict:
        agent = self._validate_agent_id(agent_id)
        with self._lock:
            data = self._load()
            data[agent] = [path for path in data.get(agent, []) if path != relative_path]
            if not data[agent]:
                data.pop(agent, None)
            self._save(data)
        return self.list_permissions(agent)

    def build_context(self, agent_id: str, paths: list[str]) -> dict:
        agent = self._validate_agent_id(agent_id)
        if not paths or len(paths) > 10:
            raise AgentAccessError("Bir so‘rovda 1 dan 10 tagacha fayl tanlang.")
        with self._lock:
            granted = set(self._load().get(agent, []))
        if len(set(paths)) != len(paths):
            raise AgentAccessError("Fayl yo‘llari takrorlanmasligi kerak.")
        attachments = []
        total_bytes = 0
        for relative_path in paths:
            if relative_path not in granted:
                raise AgentAccessError(f"Agentga bu fayl uchun read ruxsati berilmagan: {relative_path}")
            try:
                target = workspace_service.resolve(relative_path)
            except WorkspaceError as exc:
                raise AgentAccessError(str(exc)) from exc
            if target.is_symlink() or not target.is_file():
                raise AgentAccessError("Ruxsat berilgan fayl endi mavjud emas.")
            size = target.stat().st_size
            total_bytes += size
            if size > self.MAX_CONTEXT_FILE_BYTES or total_bytes > 20 * 1024 * 1024:
                raise AgentAccessError("Tanlangan fayllar umumiy hajmi 20 MB dan oshmasligi kerak.")
            suffix = target.suffix.lower()
            if suffix in self.IMAGE_TYPES:
                attachments.append({
                    "path": relative_path, "name": target.name, "kind": "image",
                    "media_type": self.IMAGE_TYPES[suffix],
                    "content_base64": base64.b64encode(target.read_bytes()).decode("ascii"),
                })
            else:
                if size > workspace_service.MAX_READ_BYTES:
                    raise AgentAccessError(f"Matnli fayl 2 MB limitdan katta: {relative_path}")
                try:
                    content = target.read_text(encoding="utf-8")
                except UnicodeDecodeError as exc:
                    raise AgentAccessError(f"Fayl matn formatida emas: {relative_path}") from exc
                attachments.append({"path": relative_path, "name": target.name, "kind": "text", "content": content})
        return {"agent_id": agent, "attachments": attachments}


agent_access_service = AgentAccessService()

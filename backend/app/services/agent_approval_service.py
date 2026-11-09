from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.services.app_data import get_data_dir, get_store_path

from app.services.agent_control_service import AgentControlError, agent_control_service
from app.services.workspace_service import WorkspaceError, workspace_service


class AgentApprovalError(ValueError):
    pass


class AgentApprovalService:
    """One-shot, path-scoped approval for replacing an existing workspace text file."""

    TTL_MINUTES = 10
    MAX_CONTENT_BYTES = 2 * 1024 * 1024

    def __init__(self, store_path: Path | None = None) -> None:
        self.store_path = store_path or (get_data_dir() / "agent_approvals.json")
        self._legacy_store_path = (
            Path(__file__).resolve().parents[2] / ".nexus" / "agent_approvals.json"
            if store_path is None else None
        )
        self._lock = threading.RLock()

    @staticmethod
    def _agent_id(agent_id: str) -> str:
        value = agent_id.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value):
            raise AgentApprovalError("Agent ID formati noto‘g‘ri.")
        return value

    def _mode_check(self, agent_id: str) -> None:
        try:
            state = agent_control_service.get(agent_id)
        except AgentControlError as exc:
            raise AgentApprovalError(str(exc)) from exc
        if state["isolated"] or state["mode"] != "approval_required":
            raise AgentApprovalError("Faylni o‘zgartirish taklifi uchun agent approval_required rejimida bo‘lishi kerak.")

    def _load(self) -> dict[str, Any]:
        if self._legacy_store_path is not None and not self.store_path.exists():
            get_store_path(self.store_path.name, self._legacy_store_path)
        try:
            value = json.loads(self.store_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}
        except (OSError, json.JSONDecodeError) as exc:
            raise AgentApprovalError("Tasdiqlash navbatini o‘qib bo‘lmadi.") from exc
        if not isinstance(value, dict):
            raise AgentApprovalError("Tasdiqlash navbati formati noto‘g‘ri.")
        return value

    def _save(self, data: dict[str, Any]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.store_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.store_path)

    @staticmethod
    def _file_state(relative_path: str) -> tuple[Path, bytes, str]:
        if (
            not isinstance(relative_path, str) or not relative_path or len(relative_path) > 500
            or "\x00" in relative_path or "\\" in relative_path or relative_path.startswith("/")
            or re.match(r"^[A-Za-z]:", relative_path)
            or any(part in {"", ".", ".."} for part in relative_path.split("/"))
        ):
            raise AgentApprovalError("Workspace fayl yo‘li noto‘g‘ri.")
        lexical = workspace_service.root.joinpath(*relative_path.split("/"))
        current = lexical
        while current != workspace_service.root and current != current.parent:
            if current.is_symlink():
                raise AgentApprovalError("Symlink orqali fayl o‘zgartirishga ruxsat yo‘q.")
            current = current.parent
        try:
            target = workspace_service.resolve(relative_path)
        except WorkspaceError as exc:
            raise AgentApprovalError(str(exc)) from exc
        if target.is_symlink() or not target.is_file():
            raise AgentApprovalError("Faqat mavjud oddiy workspace faylini almashtirish mumkin.")
        raw = target.read_bytes()
        if len(raw) > AgentApprovalService.MAX_CONTENT_BYTES:
            raise AgentApprovalError("Mavjud fayl 2 MB limitdan katta.")
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AgentApprovalError("Faqat UTF-8 matnli fayllarni o‘zgartirish mumkin.") from exc
        return target, raw, hashlib.sha256(raw).hexdigest()

    def create_request(self, agent_id: str, relative_path: str, proposed_content: str) -> dict[str, Any]:
        agent = self._agent_id(agent_id)
        self._mode_check(agent)
        if not isinstance(proposed_content, str) or len(proposed_content.encode("utf-8")) > self.MAX_CONTENT_BYTES:
            raise AgentApprovalError("Taklif qilinayotgan matn 2 MB limitdan katta yoki noto‘g‘ri.")
        target, _, original_hash = self._file_state(relative_path)
        request_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        item = {
            "request_id": request_id,
            "agent_id": agent,
            "path": target.relative_to(workspace_service.root).as_posix(),
            "operation": "replace_file",
            "proposed_content": proposed_content,
            "original_sha256": original_hash,
            "proposed_sha256": hashlib.sha256(proposed_content.encode("utf-8")).hexdigest(),
            "status": "pending",
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=self.TTL_MINUTES)).isoformat(),
            "decided_at": None,
            "result": None,
        }
        with self._lock:
            data = self._load()
            data[request_id] = item
            self._save(data)
        return self._public(item, include_content=True)

    @staticmethod
    def _public(item: dict[str, Any], include_content: bool = False) -> dict[str, Any]:
        result = {key: value for key, value in item.items() if key != "proposed_content"}
        if include_content:
            result["proposed_content"] = item["proposed_content"]
        return result

    def list_requests(self, agent_id: str, pending_only: bool = True) -> dict[str, Any]:
        agent = self._agent_id(agent_id)
        now = datetime.now(timezone.utc)
        with self._lock:
            data = self._load()
            changed = False
            items = []
            for item in data.values():
                if item.get("agent_id") != agent:
                    continue
                if item.get("status") == "pending" and datetime.fromisoformat(item["expires_at"]) <= now:
                    item["status"] = "expired"
                    item["decided_at"] = now.isoformat()
                    changed = True
                if not pending_only or item.get("status") == "pending":
                    items.append(self._public(item, include_content=True))
            if changed:
                self._save(data)
        items.sort(key=lambda item: item["created_at"], reverse=True)
        return {"agent_id": agent, "requests": items}

    def decide(self, agent_id: str, request_id: str, approve: bool) -> dict[str, Any]:
        agent = self._agent_id(agent_id)
        if not re.fullmatch(r"[a-f0-9]{32}", request_id or ""):
            raise AgentApprovalError("Tasdiqlash so‘rovi ID noto‘g‘ri.")
        if approve:
            self._mode_check(agent)
        with self._lock:
            data = self._load()
            item = data.get(request_id)
            if not isinstance(item, dict) or item.get("agent_id") != agent:
                raise AgentApprovalError("Tasdiqlash so‘rovi topilmadi.")
            if item.get("status") != "pending":
                raise AgentApprovalError("Bu so‘rov allaqachon ko‘rib chiqilgan yoki muddati tugagan.")
            now = datetime.now(timezone.utc)
            if datetime.fromisoformat(item["expires_at"]) <= now:
                item["status"] = "expired"
                item["decided_at"] = now.isoformat()
                self._save(data)
                raise AgentApprovalError("Tasdiqlash muddati tugagan.")
            if not approve:
                item["status"] = "rejected"
                item["decided_at"] = now.isoformat()
                self._save(data)
                return self._public(item)

            target, _, current_hash = self._file_state(item["path"])
            if current_hash != item["original_sha256"]:
                item["status"] = "stale"
                item["decided_at"] = now.isoformat()
                item["result"] = "File changed after the proposal; a new proposal is required."
                self._save(data)
                raise AgentApprovalError("Fayl taklif yaratilganidan keyin o‘zgargan. Yangi taklif so‘rang.")
            content = item["proposed_content"]
            if hashlib.sha256(content.encode("utf-8")).hexdigest() != item["proposed_sha256"]:
                item["status"] = "invalid"
                item["decided_at"] = now.isoformat()
                self._save(data)
                raise AgentApprovalError("Taklif mazmuni tekshiruvdan o‘tmadi.")

            # Consume the request before writing; a crash cannot make it reusable.
            item["status"] = "applying"
            item["decided_at"] = now.isoformat()
            self._save(data)
            fd, temp_name = tempfile.mkstemp(prefix=".nexus-approved-", dir=str(target.parent))
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                latest_hash = hashlib.sha256(target.read_bytes()).hexdigest()
                if latest_hash != item["original_sha256"]:
                    os.unlink(temp_name)
                    item["status"] = "stale"
                    item["result"] = "File changed immediately before replacement."
                    self._save(data)
                    raise AgentApprovalError("Fayl tasdiqlash vaqtida o‘zgardi. Yangi taklif talab etiladi.")
                os.replace(temp_name, target)
                item["status"] = "approved"
                item["result"] = "File replacement applied."
                self._save(data)
            except OSError as exc:
                try:
                    os.unlink(temp_name)
                except OSError:
                    pass
                item["status"] = "failed"
                item["result"] = "Approved write failed."
                self._save(data)
                raise AgentApprovalError("Tasdiqlangan faylni saqlab bo‘lmadi.") from exc
            return self._public(item)


agent_approval_service = AgentApprovalService()

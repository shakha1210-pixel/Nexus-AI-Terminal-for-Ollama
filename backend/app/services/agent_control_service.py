from __future__ import annotations

import asyncio
import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AgentControlError(ValueError):
    pass


class AgentControlService:
    MODES = {"read_only", "approval_required", "autopilot", "locked"}

    def __init__(self, storage_dir: Path | None = None) -> None:
        root = storage_dir or (Path(__file__).resolve().parents[2] / ".nexus")
        self.file_path = root / "agent_controls.json"
        self._lock = threading.RLock()
        self._active_requests: dict[str, set[asyncio.Task[Any]]] = {}

    @staticmethod
    def _agent_id(agent_id: str) -> str:
        value = agent_id.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value):
            raise AgentControlError("Agent ID formati noto‘g‘ri.")
        return value

    def _read(self) -> dict[str, Any]:
        try:
            value = json.loads(self.file_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except FileNotFoundError:
            return {}
        except (OSError, json.JSONDecodeError):
            raise AgentControlError("Agent boshqaruv sozlamalarini o‘qib bo‘lmadi.")

    def _write(self, value: dict[str, Any]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.file_path.with_suffix(".tmp")
        temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temp, self.file_path)

    def get(self, agent_id: str) -> dict[str, Any]:
        agent = self._agent_id(agent_id)
        with self._lock:
            data = self._read().get(agent, {})
            if not isinstance(data, dict):
                data = {}
            mode = data.get("mode", "read_only")
            if mode not in self.MODES:
                mode = "read_only"
            return {
                "agent_id": agent,
                "mode": mode,
                "isolated": bool(data.get("isolated", False)),
                "reason": data.get("reason"),
                "updated_at": data.get("updated_at"),
            }

    def set_mode(self, agent_id: str, mode: str) -> dict[str, Any]:
        agent = self._agent_id(agent_id)
        if mode not in self.MODES:
            raise AgentControlError("Access mode noto‘g‘ri.")
        with self._lock:
            all_data = self._read()
            current = all_data.get(agent, {})
            current = current if isinstance(current, dict) else {}
            current["mode"] = mode
            if mode == "locked":
                current["isolated"] = True
                current["reason"] = "Locked by access policy"
                for active in self._active_requests.get(agent, set()):
                    if not active.done():
                        active.cancel()
            current["updated_at"] = datetime.now(timezone.utc).isoformat()
            all_data[agent] = current
            self._write(all_data)
        return self.get(agent)

    def isolate(self, agent_id: str, reason: str) -> dict[str, Any]:
        agent = self._agent_id(agent_id)
        reason = (reason or "Manual isolation").strip()[:500]
        with self._lock:
            all_data = self._read()
            current = all_data.get(agent, {})
            current = current if isinstance(current, dict) else {}
            current.update({
                "mode": "locked",
                "isolated": True,
                "reason": reason or "Manual isolation",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            all_data[agent] = current
            self._write(all_data)
            for active in self._active_requests.get(agent, set()):
                if not active.done():
                    active.cancel()
        return self.get(agent)

    def release(self, agent_id: str) -> dict[str, Any]:
        agent = self._agent_id(agent_id)
        with self._lock:
            all_data = self._read()
            current = all_data.get(agent, {})
            current = current if isinstance(current, dict) else {}
            current["isolated"] = False
            current["reason"] = None
            current["mode"] = "read_only"
            current["updated_at"] = datetime.now(timezone.utc).isoformat()
            all_data[agent] = current
            self._write(all_data)
        return self.get(agent)

    def register_request(self, agent_id: str, task: asyncio.Task[Any]) -> None:
        agent = self._agent_id(agent_id)
        with self._lock:
            self._active_requests.setdefault(agent, set()).add(task)

    def unregister_request(self, agent_id: str, task: asyncio.Task[Any]) -> None:
        agent = self._agent_id(agent_id)
        with self._lock:
            tasks = self._active_requests.get(agent)
            if tasks is not None:
                tasks.discard(task)
                if not tasks:
                    self._active_requests.pop(agent, None)


agent_control_service = AgentControlService()

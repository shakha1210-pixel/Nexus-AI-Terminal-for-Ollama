from __future__ import annotations

import base64
import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.services.agent_access_service import AgentAccessError, agent_access_service
from app.services.workspace_service import workspace_service


class AgentSandboxError(ValueError):
    pass


class AgentSandboxService:
    """Creates an idle, network-disabled Docker container with a read-only grant snapshot."""

    MAX_FILES = 10
    MAX_SNAPSHOT_BYTES = 20 * 1024 * 1024
    COMMAND_TIMEOUT_SECONDS = 20

    def __init__(
        self,
        *,
        storage_root: Path | None = None,
        docker_binary: str | None = None,
        image: str | None = None,
    ) -> None:
        self.storage_root = (storage_root or (Path(__file__).resolve().parents[2] / ".nexus" / "sandboxes")).resolve()
        self.docker_binary = docker_binary or os.getenv("NEXUS_DOCKER_BINARY", "docker")
        self.image = image or os.getenv("NEXUS_SANDBOX_IMAGE", "python:3.12-slim")

    @staticmethod
    def _agent_id(agent_id: str) -> str:
        value = agent_id.strip()
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}", value):
            raise AgentSandboxError("Agent ID formati noto‘g‘ri.")
        return value

    def _name(self, agent_id: str) -> str:
        digest = hashlib.sha256(agent_id.encode("utf-8")).hexdigest()[:16]
        return f"nexus-agent-{digest}"

    def _stage_path(self, agent_id: str) -> Path:
        path = self.storage_root / self._name(agent_id)
        if not path.resolve().is_relative_to(self.storage_root):
            raise AgentSandboxError("Sandbox staging yo‘li xavfsiz emas.")
        return path

    def _docker(self, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                [self.docker_binary, *args],
                capture_output=True,
                text=True,
                timeout=self.COMMAND_TIMEOUT_SECONDS,
                check=False,
            )
        except FileNotFoundError as exc:
            raise AgentSandboxError("Docker CLI topilmadi. Sandbox ishga tushirilmadi.") from exc
        except subprocess.TimeoutExpired as exc:
            raise AgentSandboxError("Docker buyrug‘i vaqt limitidan oshdi.") from exc
        if check and result.returncode != 0:
            detail = (result.stderr or result.stdout or "Docker buyrug‘i bajarilmadi.").strip()
            raise AgentSandboxError(detail[:500])
        return result

    def _ensure_docker(self) -> None:
        self._docker(["info", "--format", "{{.ServerVersion}}"])

    def _container_status(self, name: str) -> str:
        result = self._docker(["inspect", "--format", "{{.State.Status}}", name], check=False)
        if result.returncode != 0:
            return "absent"
        return result.stdout.strip() or "unknown"

    def _remove_stage(self, stage: Path) -> None:
        if not stage.exists() or stage.is_symlink():
            return
        for item in stage.rglob("*"):
            if item.is_dir() and not item.is_symlink():
                item.chmod(0o700)
            elif not item.is_symlink():
                item.chmod(0o600)
        stage.chmod(0o700)
        shutil.rmtree(stage)

    def _write_snapshot(self, agent_id: str, paths: list[str]) -> Path:
        try:
            context = agent_access_service.build_context(agent_id, paths)
        except AgentAccessError as exc:
            raise AgentSandboxError(str(exc)) from exc
        if len(context["attachments"]) > self.MAX_FILES:
            raise AgentSandboxError("Sandbox uchun ko‘pi bilan 10 ta fayl tanlash mumkin.")

        stage = self._stage_path(agent_id)
        self.storage_root.mkdir(parents=True, exist_ok=True)
        if stage.is_symlink():
            raise AgentSandboxError("Sandbox staging papkasi symlink bo‘lishi mumkin emas.")
        if stage.exists():
            shutil.rmtree(stage)
        stage.mkdir(mode=0o700)

        total = 0
        try:
            for item in context["attachments"]:
                relative = Path(item["path"])
                if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
                    raise AgentSandboxError("Ruxsatli fayl yo‘li sandbox uchun yaroqsiz.")
                destination = stage / relative
                if not destination.resolve().is_relative_to(stage.resolve()):
                    raise AgentSandboxError("Fayl sandbox tashqarisiga chiqadi.")
                destination.parent.mkdir(parents=True, exist_ok=True)
                if item["kind"] == "image":
                    data = base64.b64decode(item["content_base64"], validate=True)
                else:
                    data = item["content"].encode("utf-8")
                total += len(data)
                if total > self.MAX_SNAPSHOT_BYTES:
                    raise AgentSandboxError("Sandbox fayllari umumiy hajmi 20 MB dan oshdi.")
                destination.write_bytes(data)
                destination.chmod(0o444)
            for directory in sorted((p for p in stage.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
                directory.chmod(0o555)
            stage.chmod(0o555)
            return stage
        except Exception:
            try:
                self._remove_stage(stage)
            except OSError:
                pass
            raise

    def start(self, agent_id: str, paths: list[str]) -> dict[str, Any]:
        agent = self._agent_id(agent_id)
        if not paths or len(paths) > self.MAX_FILES or len(set(paths)) != len(paths):
            raise AgentSandboxError("Sandbox uchun 1–10 ta takrorlanmaydigan ruxsatli fayl tanlang.")
        name = self._name(agent)
        self._ensure_docker()
        state = self._container_status(name)
        if state == "running":
            raise AgentSandboxError("Bu agent uchun sandbox allaqachon ishga tushgan.")
        if state != "absent":
            self._docker(["rm", "--force", name], check=False)

        stage = self._write_snapshot(agent, paths)
        mount = f"type=bind,src={stage},dst=/workspace,readonly"
        if "," in str(stage):
            self._remove_stage(stage)
            raise AgentSandboxError("Workspace yo‘lida vergul bor; Docker mount xavfsiz tuzilmadi.")

        command = [
            "run", "--detach", "--pull=never", "--name", name,
            "--network", "none",
            "--read-only",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges:true",
            "--pids-limit", "64",
            "--memory", "512m",
            "--cpus", "1.0",
            "--user", "65532:65532",
            "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=64m",
            "--mount", mount,
            "--workdir", "/workspace",
            "--entrypoint", "python",
            self.image,
            "-c", "import time; time.sleep(10**9)",
        ]
        try:
            result = self._docker(command)
        except Exception:
            try:
                self._remove_stage(stage)
            except OSError:
                pass
            raise
        return {
            "agent_id": agent,
            "container": name,
            "status": "running",
            "network": "none",
            "workspace_access": "read_only_snapshot",
            "files": len(paths),
            "container_id": result.stdout.strip()[:64],
        }

    def stop(self, agent_id: str) -> dict[str, Any]:
        agent = self._agent_id(agent_id)
        name = self._name(agent)
        self._ensure_docker()
        state = self._container_status(name)
        if state != "absent":
            self._docker(["rm", "--force", name])
        stage = self._stage_path(agent)
        self._remove_stage(stage)
        return {"agent_id": agent, "container": name, "status": "stopped"}

    def status(self, agent_id: str) -> dict[str, Any]:
        agent = self._agent_id(agent_id)
        name = self._name(agent)
        try:
            self._ensure_docker()
            state = self._container_status(name)
            return {"agent_id": agent, "container": name, "available": True, "status": state}
        except AgentSandboxError as exc:
            return {"agent_id": agent, "container": name, "available": False, "status": "unavailable", "reason": str(exc)}


agent_sandbox_service = AgentSandboxService()

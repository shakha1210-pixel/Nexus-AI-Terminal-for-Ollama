from __future__ import annotations

import asyncio
import json
import os
import re
import tempfile
import uuid
from pathlib import Path

from app.services.agent_access_service import AgentAccessError, agent_access_service
from app.services.workspace_service import WorkspaceError, workspace_service


class AgentSandboxError(RuntimeError):
    pass


class AgentSandboxService:
    """Runs the narrowly scoped file-read tool in a disposable, networkless container."""

    IMAGE = os.getenv("NEXUS_AGENT_SANDBOX_IMAGE", "nexus-agent-sandbox:py311")
    DOCKER_BIN = os.getenv("NEXUS_DOCKER_BIN", "docker")
    TIMEOUT_SECONDS = 12
    MAX_OUTPUT_BYTES = 12 * 1024 * 1024 + 4096
    READ_SCRIPT = (
        "import json,pathlib,sys; "
        "p=pathlib.Path('/input/file'); "
        "b=p.read_bytes(); "
        "sys.exit(3) if len(b)>2097152 else None; "
        "print(json.dumps({'content':b.decode('utf-8')}))"
    )

    @staticmethod
    def _validate_relative_path(relative_path: str) -> None:
        if (
            not isinstance(relative_path, str)
            or not relative_path
            or len(relative_path) > 500
            or "\x00" in relative_path
            or "\\" in relative_path
            or relative_path.startswith("/")
            or re.match(r"^[A-Za-z]:", relative_path)
            or any(part in {"", ".", ".."} for part in relative_path.split("/"))
        ):
            raise AgentSandboxError("Sandbox uchun fayl yo‘li noto‘g‘ri.")

    def _command(self, source: Path, container_name: str) -> list[str]:
        # Docker's --mount uses comma-separated fields; reject ambiguous host paths.
        source_text = str(source)
        if "," in source_text:
            raise AgentSandboxError("Docker bind-mount yo‘lida vergul bo‘lishi mumkin emas.")
        return [
            self.DOCKER_BIN, "run", "--rm", "--pull=never", "--name", container_name,
            "--network=none", "--read-only", "--cap-drop=ALL",
            "--security-opt=no-new-privileges", "--pids-limit=16",
            "--memory=96m", "--memory-swap=96m", "--cpus=0.50", "--user=65532:65532",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=1m",
            "--mount", f"type=bind,source={source_text},target=/input/file,readonly",
            self.IMAGE, "-c", self.READ_SCRIPT,
        ]


    async def _force_remove(self, container_name: str) -> None:
        """Best-effort cleanup if the Docker client is cancelled while the container runs."""
        cleanup: asyncio.subprocess.Process | None = None
        try:
            cleanup = await asyncio.create_subprocess_exec(
                self.DOCKER_BIN, "rm", "-f", container_name,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(cleanup.communicate(), timeout=4)
        except (FileNotFoundError, asyncio.TimeoutError, OSError):
            if cleanup is not None and cleanup.returncode is None:
                cleanup.kill()
                await cleanup.communicate()

    async def read_granted_file(self, agent_id: str, relative_path: str) -> dict:
        self._validate_relative_path(relative_path)
        try:
            permissions = agent_access_service.list_permissions(agent_id)
            granted = {item["path"] for item in permissions["permissions"]}
            if relative_path not in granted:
                raise AgentSandboxError("Agentga bu fayl uchun aniq read ruxsati berilmagan.")
            source = workspace_service.resolve(relative_path)
        except (AgentAccessError, WorkspaceError) as exc:
            raise AgentSandboxError(str(exc)) from exc

        if source.is_symlink() or not source.is_file():
            raise AgentSandboxError("Faqat mavjud oddiy faylni sandbox orqali o‘qish mumkin.")
        if source.stat().st_size > 2 * 1024 * 1024:
            raise AgentSandboxError("Fayl 2 MB limitdan katta.")
        staged_path: str | None = None
        process: asyncio.subprocess.Process | None = None
        container_name = "nexus-agent-read-" + uuid.uuid4().hex
        try:
            # Stage only the explicitly granted file. The container never receives
            # a mount of the workspace directory or any other host path.
            file_bytes = source.read_bytes()
            if len(file_bytes) > 2 * 1024 * 1024:
                raise AgentSandboxError("Fayl 2 MB limitdan katta.")
            fd, staged_path = tempfile.mkstemp(prefix="nexus-agent-input-")
            with os.fdopen(fd, "wb") as staged:
                staged.write(file_bytes)
            os.chmod(staged_path, 0o444)
            process = await asyncio.create_subprocess_exec(
                *self._command(Path(staged_path), container_name),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=self.TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError as exc:
                process.kill()
                await process.communicate()
                await asyncio.shield(self._force_remove(container_name))
                raise AgentSandboxError("Sandbox vaqt limiti tugadi; container to‘xtatildi.") from exc
            if process.returncode != 0:
                detail = stderr.decode("utf-8", errors="replace")[:500].strip()
                raise AgentSandboxError(
                    "Sandbox ishga tushmadi yoki faylni o‘qiy olmadi. "
                    "Docker daemon va nexus-agent-sandbox:py311 image holatini tekshiring. "
                    + detail
                )
            if len(stdout) > self.MAX_OUTPUT_BYTES:
                raise AgentSandboxError("Sandbox javobi ruxsat etilgan hajmdan katta.")
            try:
                payload = json.loads(stdout.decode("utf-8"))
                content = payload["content"]
                if not isinstance(content, str):
                    raise ValueError("content is not text")
            except (UnicodeDecodeError, json.JSONDecodeError, KeyError, ValueError) as exc:
                raise AgentSandboxError("Sandbox javobi noto‘g‘ri formatda.") from exc
            return {"path": relative_path, "content": content, "sandbox": "docker"}
        except FileNotFoundError as exc:
            raise AgentSandboxError(
                "Docker CLI topilmadi. Agent xavfsizlik sababli sandboxsiz ishlamaydi."
            ) from exc
        except asyncio.CancelledError:
            if process is not None and process.returncode is None:
                process.kill()
                await process.communicate()
            await asyncio.shield(self._force_remove(container_name))
            raise
        finally:
            if staged_path is not None:
                try:
                    os.chmod(staged_path, 0o600)
                    os.unlink(staged_path)
                except OSError:
                    pass


agent_sandbox_service = AgentSandboxService()

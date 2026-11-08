import asyncio
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import httpx

from app.config import settings
from app.services.ollama_service import ollama_service

TEMPLATE = Path(__file__).resolve().parent.parent / "kaggle_templates" / "server.py.tpl"


class KaggleError(Exception):
    pass


class KaggleService:
    def __init__(self) -> None:
        self.state = "idle"
        self.model: str | None = None
        self.message = "Kaggle ishga tushirilmagan."

    @property
    def slug(self) -> str:
        return f"{settings.kaggle_username}/{settings.kaggle_kernel_name}"

    @property
    def endpoint(self) -> str | None:
        return f"https://{settings.ngrok_domain}" if settings.ngrok_domain else None

    def _auth(self) -> tuple[str, str]:
        return (settings.tunnel_user, settings.tunnel_password)

    def _check_config(self) -> None:
        missing = [n for n, v in {
            "KAGGLE_USERNAME": settings.kaggle_username,
            "KAGGLE_KEY": settings.kaggle_key,
            "NGROK_DOMAIN": settings.ngrok_domain,
            "TUNNEL_PASSWORD": settings.tunnel_password,
        }.items() if not v]
        if missing:
            raise KaggleError("backend/.env da to‘ldirilmagan: " + ", ".join(missing))

    def _run(self, args: list[str]) -> str:
        env = {**os.environ, "KAGGLE_USERNAME": settings.kaggle_username, "KAGGLE_KEY": settings.kaggle_key}
        try:
            proc = subprocess.run(["kaggle", *args], env=env, capture_output=True, text=True, timeout=120)
        except FileNotFoundError as exc:
            raise KaggleError("`kaggle` buyrug‘i topilmadi. `pip install -r requirements.txt` ni qayta ishga tushiring.") from exc
        except subprocess.TimeoutExpired as exc:
            raise KaggleError("Kaggle API vaqti tugadi.") from exc
        out = (proc.stdout + "\n" + proc.stderr).strip()
        if proc.returncode != 0:
            raise KaggleError(out[-400:] or "Kaggle buyrug‘i xato bilan tugadi.")
        return out

    def _push_sync(self, model: str) -> None:
        code = (TEMPLATE.read_text(encoding="utf-8")
                .replace("__MODEL__", model)
                .replace("__NGROK_DOMAIN__", settings.ngrok_domain)
                .replace("__TUNNEL_USER__", settings.tunnel_user))
        meta = {
            "id": self.slug,
            "title": settings.kaggle_kernel_name,
            "code_file": "server.py",
            "language": "python",
            "kernel_type": "script",
            "is_private": True,
            "enable_gpu": True,
            "enable_internet": True,
            "dataset_sources": [], "competition_sources": [], "kernel_sources": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "server.py").write_text(code, encoding="utf-8")
            (Path(tmp) / "kernel-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
            self._run(["kernels", "push", "-p", tmp])

    def _status_sync(self) -> str:
        out = self._run(["kernels", "status", self.slug])
        match = re.search(r'status\s+"?([A-Za-z_.]+)"?', out)
        return match.group(1).split(".")[-1].upper() if match else "UNKNOWN"

    async def _probe(self) -> tuple[bool, bool]:
        """(tunnel javob beryaptimi, model yuklanganmi)"""
        if not self.endpoint:
            return False, False
        try:
            async with httpx.AsyncClient(timeout=6, auth=self._auth()) as client:
                r = await client.get(f"{self.endpoint}/api/tags")
                if r.status_code != 200:
                    return False, False
                names = [(m.get("name") or "") for m in r.json().get("models", [])]
                wanted = (self.model or "").split(":")[0]
                return True, any(n.split(":")[0] == wanted for n in names)
        except (httpx.HTTPError, ValueError):
            return False, False

    async def start(self, model: str) -> None:
        self._check_config()
        self.state, self.model, self.message = "pushing", model, "Notebook Kaggle’ga yuborilmoqda…"
        try:
            await asyncio.to_thread(self._push_sync, model)
        except KaggleError as exc:
            self.state, self.message = "error", str(exc)
            raise
        self.state, self.message = "queued", "Kaggle navbatida. GPU ajratilishi kutilmoqda…"

    async def refresh(self) -> dict:
        if self.state in ("idle", "pushing", "error") or not settings.kaggle_username:
            return self.snapshot()
        try:
            status = await asyncio.to_thread(self._status_sync)
        except KaggleError as exc:
            self.message = str(exc)
            return self.snapshot()

        if status in ("QUEUED", "NEW", "UNKNOWN"):
            self.state, self.message = "queued", "Kaggle navbatida…"
        elif status == "RUNNING":
            tunnel_up, model_ready = await self._probe()
            if tunnel_up and model_ready:
                self.state, self.message = "online", f"{self.model} tayyor."
            elif tunnel_up:
                self.state, self.message = "starting", f"Model yuklanmoqda: {self.model}…"
            else:
                self.state, self.message = "starting", "Ollama va tunnel o‘rnatilmoqda…"
        elif status in ("COMPLETE", "CANCEL_REQUESTED", "CANCEL_ACKNOWLEDGED"):
            self.state, self.message = "stopped", "Kaggle sessiyasi tugagan."
            if ollama_service.mode == "kaggle":
                ollama_service.use_local()
        elif status == "ERROR":
            self.state, self.message = "error", "Kaggle notebook xato bilan to‘xtadi. Kaggle’da loglarni ko‘ring."
            if ollama_service.mode == "kaggle":
                ollama_service.use_local()
        return self.snapshot()

    def set_mode(self, mode: str) -> None:
        if mode == "local":
            ollama_service.use_local()
            return
        if self.state != "online" or not self.endpoint:
            raise KaggleError("Kaggle hali tayyor emas (holat: online bo‘lishi kerak).")
        ollama_service.use_remote(self.endpoint, self._auth())

    def snapshot(self) -> dict:
        online = self.state == "online" and self.endpoint
        return {
            "state": self.state,
            "model": self.model,
            "kernel": self.slug if settings.kaggle_username else None,
            "endpoint": self.endpoint if online else None,
            "openai_base_url": f"{self.endpoint}/v1" if online else None,
            "mode": ollama_service.mode,
            "message": self.message,
        }


kaggle_service = KaggleService()

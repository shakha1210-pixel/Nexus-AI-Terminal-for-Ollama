from __future__ import annotations

import csv
import io
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.config import settings
from app.services.app_data import get_data_dir
from app.services.secrets_service import secrets_service


class KaggleNotebookError(ValueError):
    pass


class KaggleNotebookService:
    """Search Kaggle kernels and download notebook source without executing it."""

    MAX_RESULTS = 20
    MAX_NOTEBOOK_BYTES = 20 * 1024 * 1024
    REF_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}/[A-Za-z0-9_-]{1,120}$")

    def __init__(self, *, data_dir: Path | None = None, kaggle_binary: str | None = None) -> None:
        self.data_dir = (data_dir or get_data_dir()).resolve()
        self.kaggle_binary = kaggle_binary or os.getenv("NEXUS_KAGGLE_BINARY", "kaggle")

    @staticmethod
    def _credentials() -> tuple[str, str]:
        username = settings.kaggle_username or os.getenv("KAGGLE_USERNAME", "")
        key = settings.kaggle_key or os.getenv("KAGGLE_KEY", "") or secrets_service.get("kaggle-key") or ""
        return username, key

    def _run(self, args: list[str], *, timeout: int = 120) -> str:
        username, key = self._credentials()
        if not username or not key:
            raise KaggleNotebookError(
                "Kaggle API sozlanmagan. KAGGLE_USERNAME va Kaggle API kalitini tekshiring."
            )
        env = {**os.environ, "KAGGLE_USERNAME": username, "KAGGLE_KEY": key}
        try:
            result = subprocess.run(
                [self.kaggle_binary, *args],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                env=env,
            )
        except FileNotFoundError as exc:
            raise KaggleNotebookError("Kaggle CLI topilmadi. Backend requirements faylini o‘rnating.") from exc
        except subprocess.TimeoutExpired as exc:
            raise KaggleNotebookError("Kaggle so‘rovi vaqt limitidan oshdi.") from exc
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "Kaggle API so‘rovi bajarilmadi.").strip()
            raise KaggleNotebookError(detail[-500:])
        return result.stdout

    @staticmethod
    def _parse_results(output: str) -> list[dict[str, Any]]:
        reader = csv.DictReader(io.StringIO(output))
        results: list[dict[str, Any]] = []
        for row in reader:
            ref = (row.get("ref") or row.get("Ref") or "").strip()
            if not KaggleNotebookService.REF_PATTERN.fullmatch(ref):
                continue
            votes = row.get("totalVotes") or row.get("TotalVotes") or "0"
            try:
                vote_count = max(0, int(votes))
            except (TypeError, ValueError):
                vote_count = 0
            results.append({
                "ref": ref,
                "title": (row.get("title") or row.get("Title") or ref.split("/", 1)[-1])[:200],
                "author": (row.get("author") or row.get("Author") or ref.split("/", 1)[0])[:100],
                "last_run": (row.get("lastRunTime") or row.get("LastRunTime") or "")[:64],
                "votes": vote_count,
            })
            if len(results) >= KaggleNotebookService.MAX_RESULTS:
                break
        return results

    def search(self, query: str, page: int = 1) -> dict[str, Any]:
        normalized = query.strip()
        if len(normalized) < 2 or len(normalized) > 120:
            raise KaggleNotebookError("Qidiruv so‘rovi 2–120 belgi oralig‘ida bo‘lishi kerak.")
        if not 1 <= page <= 100:
            raise KaggleNotebookError("Sahifa raqami 1–100 oralig‘ida bo‘lishi kerak.")
        output = self._run(["kernels", "list", "-s", normalized, "-p", str(page), "--csv"])
        items = self._parse_results(output)
        return {"query": normalized, "page": page, "items": items}

    def download(self, ref: str) -> Path:
        normalized = ref.strip()
        if not self.REF_PATTERN.fullmatch(normalized):
            raise KaggleNotebookError("Kaggle notebook manzili noto‘g‘ri. owner/slug formatidan foydalaning.")

        self.data_dir.mkdir(parents=True, exist_ok=True)
        destination_dir = (self.data_dir / "kaggle-notebooks").resolve()
        if not destination_dir.is_relative_to(self.data_dir):
            raise KaggleNotebookError("Notebook saqlash yo‘li xavfsiz emas.")
        destination_dir.mkdir(parents=True, exist_ok=True)
        owner, slug = normalized.split("/", 1)

        with tempfile.TemporaryDirectory(prefix="nexus-kaggle-") as temp:
            temp_dir = Path(temp).resolve()
            self._run(["kernels", "pull", normalized, "-p", str(temp_dir)])
            candidates = [
                path for path in temp_dir.rglob("*.ipynb")
                if path.is_file() and not path.is_symlink()
            ]
            if not candidates:
                raise KaggleNotebookError(
                    "Ushbu Kaggle kernel .ipynb notebook faylini bermadi. Faqat notebook formatidagi manbalar yuklanadi."
                )
            source = candidates[0].resolve()
            if not source.is_relative_to(temp_dir):
                raise KaggleNotebookError("Yuklangan fayl vaqtinchalik papkadan tashqariga chiqdi.")
            if source.stat().st_size > self.MAX_NOTEBOOK_BYTES:
                raise KaggleNotebookError("Notebook 20 MB limitdan katta.")
            payload = source.read_bytes()
            if not payload.startswith(b"{") or b'"cells"' not in payload[:4096]:
                raise KaggleNotebookError("Yuklangan fayl yaroqli Jupyter notebook formatida emas.")

        target = destination_dir / f"{owner}__{slug}.ipynb"
        temporary = destination_dir / f".{owner}__{slug}.tmp"
        try:
            temporary.write_bytes(payload)
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()
        return target


kaggle_notebook_service = KaggleNotebookService()

import csv
import io
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.config import settings

_KERNEL_REF = re.compile(r"^[A-Za-z0-9_-]{1,50}/[A-Za-z0-9_-]{1,100}$")
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_NOTEBOOK_DIR = _BACKEND_DIR / "data" / "kaggle"


class KaggleServiceError(RuntimeError):
    """Raised when Kaggle CLI operations cannot be completed."""


class KaggleService:
    def _environment(self) -> dict[str, str]:
        env = os.environ.copy()
        if settings.kaggle_api_token:
            env["KAGGLE_API_TOKEN"] = settings.kaggle_api_token
        if settings.kaggle_username:
            env["KAGGLE_USERNAME"] = settings.kaggle_username
        if settings.kaggle_key:
            env["KAGGLE_KEY"] = settings.kaggle_key

        if not (env.get("KAGGLE_API_TOKEN") or (
            env.get("KAGGLE_USERNAME") and env.get("KAGGLE_KEY")
        )):
            raise KaggleServiceError(
                "Kaggle credentials are not configured. Set KAGGLE_API_TOKEN "
                "or both KAGGLE_USERNAME and KAGGLE_KEY in backend/.env."
            )
        return env

    @staticmethod
    def _cli() -> str:
        executable = shutil.which("kaggle")
        if not executable:
            raise KaggleServiceError(
                "Kaggle CLI is not installed. Install the backend requirements."
            )
        return executable

    def _run(self, args: list[str], *, timeout: int = 60) -> subprocess.CompletedProcess[str]:
        try:
            result = subprocess.run(
                [self._cli(), *args],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                env=self._environment(),
            )
        except subprocess.TimeoutExpired as exc:
            raise KaggleServiceError("Kaggle request timed out. Please try again.") from exc
        except OSError as exc:
            raise KaggleServiceError("Could not start the Kaggle CLI.") from exc

        if result.returncode != 0:
            # Do not forward raw CLI output: it may contain local paths or account data.
            raise KaggleServiceError(
                "Kaggle CLI request failed. Check the credentials and notebook reference."
            )
        return result

    @staticmethod
    def _int_value(value: Any) -> int:
        try:
            return int(str(value or "0").replace(",", ""))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _is_pulled(ref: str) -> bool:
        owner, slug = ref.split("/", 1)
        return (_NOTEBOOK_DIR / owner / f"{slug}.ipynb").is_file()

    def list_notebooks(self, *, search: str | None = None, page: int = 1) -> list[dict[str, Any]]:
        args = ["kernels", "list", "--csv", "--page", str(page)]
        if search:
            args.extend(["--search", search.strip()[:120]])
        if settings.kaggle_username:
            args.extend(["--user", settings.kaggle_username])

        reader = csv.DictReader(io.StringIO(self._run(args).stdout))
        notebooks: list[dict[str, Any]] = []

        for row in reader:
            normalized = {str(key).strip().lower(): value for key, value in row.items() if key}
            ref = str(normalized.get("ref") or "").strip()
            if not _KERNEL_REF.fullmatch(ref):
                continue
            title = str(normalized.get("title") or ref.rsplit("/", 1)[-1]).strip()
            language = str(normalized.get("language") or "").strip() or None
            last_updated = str(
                normalized.get("lastruntime") or normalized.get("lastupdated")
                or normalized.get("last_run_time") or ""
            ).strip() or None
            votes = self._int_value(
                normalized.get("totalvotes") or normalized.get("votecount")
                or normalized.get("total_votes")
            )
            notebooks.append({
                "ref": ref,
                "title": title,
                "language": language,
                "votes": votes,
                "last_updated": last_updated,
                "url": f"https://www.kaggle.com/code/{ref}",
                "is_pulled": self._is_pulled(ref),
            })
        return notebooks

    def pull_notebook(self, ref: str) -> dict[str, str]:
        if not _KERNEL_REF.fullmatch(ref):
            raise KaggleServiceError("Notebook reference must use the owner/slug format.")

        owner, slug = ref.split("/", 1)
        destination = _NOTEBOOK_DIR / owner
        destination.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="nexus-kaggle-") as temporary:
            self._run(
                ["kernels", "pull", ref, "--path", temporary, "--metadata"],
                timeout=120,
            )
            candidates = list(Path(temporary).glob("*.ipynb"))
            if not candidates:
                raise KaggleServiceError(
                    "Kaggle did not return an .ipynb file for this notebook."
                )
            target = destination / f"{slug}.ipynb"
            target.write_bytes(candidates[0].read_bytes())

        return {"ref": ref, "filename": target.name, "status": "downloaded"}


kaggle_service = KaggleService()

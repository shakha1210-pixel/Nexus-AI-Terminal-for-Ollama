import httpx

from app.config import settings


class OllamaService:
    def __init__(self) -> None:
        self.local_base_url = settings.ollama_base_url.rstrip("/")
        self.base_url = self.local_base_url
        self.timeout = settings.request_timeout_seconds
        self.mode = "local"
        self.auth: tuple[str, str] | None = None

    def use_local(self) -> None:
        self.mode = "local"
        self.base_url = self.local_base_url
        self.auth = None

    def use_remote(self, base_url: str, auth: tuple[str, str]) -> None:
        self.mode = "kaggle"
        self.base_url = base_url.rstrip("/")
        self.auth = auth

    async def _get(self, path: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout, auth=self.auth) as client:
            response = await client.get(f"{self.base_url}{path}")
            response.raise_for_status()
            return response.json()

    async def get_status(self) -> dict:
        try:
            payload = await self._get("/api/version")
            version = payload.get("version")
            if not isinstance(version, str) or not version:
                return {"connected": False, "version": None, "mode": self.mode, "message": "Ollama javobi kutilgan formatda emas."}
            return {"connected": True, "version": version, "mode": self.mode, "message": "Ollama bilan aloqa o‘rnatildi."}
        except (httpx.HTTPError, ValueError) as exc:
            return {
                "connected": False,
                "version": None,
                "mode": self.mode,
                "message": f"Ollama bilan bog‘lanib bo‘lmadi: {type(exc).__name__}",
            }

    async def get_models(self) -> list[dict]:
        payload = await self._get("/api/tags")
        models = payload.get("models", [])
        if not isinstance(models, list):
            raise ValueError("Ollama models javobi noto‘g‘ri formatda.")
        result = []
        for item in models:
            details = item.get("details") or {}
            result.append({
                "name": item.get("name") or item.get("model") or "Noma’lum model",
                "size": item.get("size"),
                "modified_at": item.get("modified_at"),
                "digest": item.get("digest"),
                "family": details.get("family"),
                "parameter_size": details.get("parameter_size"),
                "quantization_level": details.get("quantization_level"),
            })
        return result

    
    async def pull_model(self, model: str):
        import json

        async with httpx.AsyncClient(timeout=None, auth=self.auth) as client:
            try:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/pull",
                    json={"name": model, "stream": True},
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            yield f"data: {line}\n\n"
            except httpx.HTTPError as exc:
                payload = json.dumps({"error": f"Ollama model yuklashda xatolik: {type(exc).__name__}"})
                yield f"data: {payload}\n\n"
        yield "data: [DONE]\n\n"

    async def delete_model(self, model: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout, auth=self.auth) as client:
            response = await client.request(
                "DELETE",
                f"{self.base_url}/api/delete",
                json={"name": model},
            )
            response.raise_for_status()
        return {"deleted": model}


ollama_service = OllamaService()

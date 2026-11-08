import httpx

from app.config import settings


class OllamaService:
    def __init__(self) -> None:
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.timeout = settings.request_timeout_seconds

    async def _get(self, path: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}{path}")
            response.raise_for_status()
            return response.json()

    async def get_status(self) -> dict:
        try:
            payload = await self._get("/api/version")
            version = payload.get("version")
            if not isinstance(version, str) or not version:
                return {"connected": False, "version": None, "message": "Ollama javobi kutilgan formatda emas."}
            return {"connected": True, "version": version, "message": "Ollama bilan aloqa o‘rnatildi."}
        except (httpx.HTTPError, ValueError) as exc:
            return {
                "connected": False,
                "version": None,
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


ollama_service = OllamaService()

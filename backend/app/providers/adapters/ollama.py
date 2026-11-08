import json
from typing import Any, AsyncIterator, Callable

import httpx

from app.providers.base import BaseAdapter, ProviderCapabilities, ProviderModel


class OllamaAdapter(BaseAdapter):
    """Native Ollama API adapter; endpoint/auth may follow the active local/Kaggle runtime."""

    def __init__(self, base_url: str | Callable[[], str], timeout: float = 30.0,
                 auth: tuple[str, str] | None | Callable[[], tuple[str, str] | None] = None,
                 provider_id: str = "ollama") -> None:
        if not provider_id.strip():
            raise ValueError("provider_id must be non-empty")
        self.provider_id = provider_id
        self._base_url = base_url
        self.timeout = timeout
        self._auth = auth

    @property
    def base_url(self) -> str:
        value = self._base_url() if callable(self._base_url) else self._base_url
        return value.rstrip("/")

    @property
    def auth(self) -> tuple[str, str] | None:
        return self._auth() if callable(self._auth) else self._auth

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout, auth=self.auth) as client:
                response = await client.get(f"{self.base_url}/api/version")
                response.raise_for_status()
                return isinstance(response.json().get("version"), str)
        except (httpx.HTTPError, ValueError):
            return False

    async def list_models(self) -> list[ProviderModel]:
        async with httpx.AsyncClient(timeout=self.timeout, auth=self.auth) as client:
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            payload = response.json()
        models = payload.get("models", [])
        if not isinstance(models, list):
            raise ValueError("Ollama returned an invalid model list.")
        result = []
        for item in models:
            if not isinstance(item, dict):
                continue
            name = item.get("name") or item.get("model")
            if not name:
                continue
            details = item.get("details") or {}
            lowered = str(name).lower()
            tool_calling = any(token in lowered for token in (
                "llama3.1", "llama3.2", "llama3.3", "qwen2.5", "qwen3",
                "mistral-nemo", "command-r", "granite3", "firefunction", "hermes3",
            ))
            vision = any(token in lowered for token in (
                "llava", "qwen-vl", "qwen2-vl", "minicpm-v", "moondream",
                "llama3.2-vision", "gemma3",
            ))
            result.append(ProviderModel(
                id=str(name), display_name=str(name),
                capabilities=ProviderCapabilities(streaming=True, tool_calling=tool_calling, vision=vision),
                metadata={key: value for key, value in {
                    "size": item.get("size"), "modified_at": item.get("modified_at"),
                    "digest": item.get("digest"), "family": details.get("family"),
                    "parameter_size": details.get("parameter_size"),
                    "quantization_level": details.get("quantization_level"),
                }.items() if value is not None},
            ))
        return result

    async def chat(self, messages: list[dict[str, Any]], model: str, **kwargs: Any) -> dict[str, Any]:
        payload = {**kwargs, "model": model, "messages": messages, "stream": False}
        async with httpx.AsyncClient(timeout=self.timeout, auth=self.auth) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            return response.json()

    async def stream(self, messages: list[dict[str, Any]], model: str, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        payload = {**kwargs, "model": model, "messages": messages, "stream": True}
        async with httpx.AsyncClient(timeout=None, auth=self.auth) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if chunk.get("error"):
                        raise RuntimeError(str(chunk["error"])[:500])
                    yield chunk
                    if chunk.get("done"):
                        break

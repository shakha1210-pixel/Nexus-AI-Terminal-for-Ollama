import json
from typing import Any, AsyncIterator

import httpx

from app.providers.base import BaseAdapter, ProviderCapabilities, ProviderModel


class OllamaAdapter(BaseAdapter):
    """Native Ollama API adapter; can target local or authenticated remote Ollama."""

    provider_id = "ollama"

    def __init__(self, base_url: str, timeout: float = 30.0, auth: tuple[str, str] | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.auth = auth

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
        return [ProviderModel(
            id=str(item.get("name") or item.get("model")),
            display_name=str(item.get("name") or item.get("model")),
            capabilities=ProviderCapabilities(streaming=True),
            metadata={key: item.get(key) for key in ("size", "modified_at", "digest") if item.get(key) is not None},
        ) for item in models if item.get("name") or item.get("model")]

    async def chat(self, messages: list[dict[str, Any]], model: str, **kwargs: Any) -> dict[str, Any]:
        payload = {"model": model, "messages": messages, "stream": False, **kwargs}
        async with httpx.AsyncClient(timeout=self.timeout, auth=self.auth) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            return response.json()

    async def stream(self, messages: list[dict[str, Any]], model: str, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        payload = {"model": model, "messages": messages, "stream": True, **kwargs}
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

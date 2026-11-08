import json
from typing import Any, AsyncIterator

import httpx

from app.providers.base import BaseAdapter, ProviderCapabilities, ProviderModel


class OpenAICompatibleAdapter(BaseAdapter):
    """Adapter for OpenAI-compatible /v1 APIs; API keys stay backend-side."""

    provider_id = "openai-compatible"

    def __init__(self, base_url: str, api_key: str | None = None, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    @property
    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers) as client:
                response = await client.get(f"{self.base_url}/models")
                response.raise_for_status()
                return isinstance(response.json().get("data"), list)
        except (httpx.HTTPError, ValueError):
            return False

    async def list_models(self) -> list[ProviderModel]:
        async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers) as client:
            response = await client.get(f"{self.base_url}/models")
            response.raise_for_status()
            payload = response.json()
        data = payload.get("data", [])
        if not isinstance(data, list):
            raise ValueError("OpenAI-compatible API returned an invalid model list.")
        return [ProviderModel(
            id=str(item["id"]),
            display_name=str(item.get("name") or item["id"]),
            # Capabilities are conservative unless explicitly supplied by a future provider manifest.
            capabilities=ProviderCapabilities(streaming=True),
            metadata={"owned_by": item.get("owned_by")} if item.get("owned_by") else {},
        ) for item in data if isinstance(item, dict) and item.get("id")]

    async def chat(self, messages: list[dict[str, Any]], model: str, **kwargs: Any) -> dict[str, Any]:
        payload = {"model": model, "messages": messages, "stream": False, **kwargs}
        async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers) as client:
            response = await client.post(f"{self.base_url}/chat/completions", json=payload)
            response.raise_for_status()
            return response.json()

    async def stream(self, messages: list[dict[str, Any]], model: str, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        payload = {"model": model, "messages": messages, "stream": True, **kwargs}
        async with httpx.AsyncClient(timeout=None, headers=self._headers) as client:
            async with client.stream("POST", f"{self.base_url}/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        yield json.loads(raw)
                    except json.JSONDecodeError:
                        continue

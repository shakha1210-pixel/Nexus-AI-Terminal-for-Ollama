import json
from typing import Any, AsyncIterator

import httpx

from app.providers.base import BaseAdapter, ProviderCapabilities, ProviderModel


class OpenAICompatibleAdapter(BaseAdapter):
    """Adapter for OpenAI-compatible /v1 APIs; normalizes responses for NEXUS runtimes."""

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
            id=str(item["id"]), display_name=str(item.get("name") or item["id"]),
            # Tool calling is advertised by the OpenAI chat-completions contract; vision remains opt-in.
            capabilities=ProviderCapabilities(streaming=True, tool_calling=True),
            metadata={"owned_by": item.get("owned_by")} if item.get("owned_by") else {},
        ) for item in data if isinstance(item, dict) and item.get("id")]

    @staticmethod
    def _normalize_message(message: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {
            "role": (message.get("role") or "assistant"),
            "content": message.get("content") or "",
        }
        calls = message.get("tool_calls") or []
        if calls:
            normalized["tool_calls"] = []
            for call in calls:
                function = call.get("function") or {}
                raw_args = function.get("arguments") or "{}"
                try:
                    arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                except json.JSONDecodeError:
                    arguments = {}
                normalized["tool_calls"].append({
                    "id": call.get("id"),
                    "function": {"name": function.get("name"), "arguments": arguments},
                })
        return normalized

    @staticmethod
    def _to_openai_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        converted: list[dict[str, Any]] = []
        tool_ids: dict[str, str] = {}
        for message in messages:
            item = dict(message)
            role = item.get("role")
            if role == "assistant" and item.get("tool_calls"):
                calls = []
                for index, call in enumerate(item["tool_calls"]):
                    function = call.get("function") or {}
                    call_id = call.get("id") or f"nexus_call_{len(converted)}_{index}"
                    tool_ids[str(function.get("name") or "")] = call_id
                    arguments = function.get("arguments") or {}
                    calls.append({"id": call_id, "type": "function", "function": {
                        "name": function.get("name"),
                        "arguments": json.dumps(arguments, ensure_ascii=False),
                    }})
                converted.append({"role": "assistant", "content": item.get("content") or None, "tool_calls": calls})
            elif role == "tool":
                name = str(item.get("tool_name") or "")
                converted.append({"role": "tool", "tool_call_id": tool_ids.get(name, "nexus_tool_call"), "content": item.get("content", "")})
            else:
                converted.append({key: value for key, value in item.items() if key in ("role", "content")})
        return converted

    async def chat(self, messages: list[dict[str, Any]], model: str, **kwargs: Any) -> dict[str, Any]:
        payload = {**kwargs, "model": model, "messages": self._to_openai_messages(messages), "stream": False}
        async with httpx.AsyncClient(timeout=self.timeout, headers=self._headers) as client:
            response = await client.post(f"{self.base_url}/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
        choices = data.get("choices") or []
        if not choices or not isinstance(choices[0].get("message"), dict):
            raise ValueError("OpenAI-compatible API returned no assistant message.")
        return {"message": self._normalize_message(choices[0]["message"]), "usage": data.get("usage")}

    async def stream(self, messages: list[dict[str, Any]], model: str, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        payload = {**kwargs, "model": model, "messages": messages, "stream": True}
        async with httpx.AsyncClient(timeout=None, headers=self._headers) as client:
            async with client.stream("POST", f"{self.base_url}/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        yield {"done": True}
                        break
                    try:
                        chunk = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    for choice in chunk.get("choices", []):
                        delta = choice.get("delta") or {}
                        content = delta.get("content")
                        if content:
                            yield {"message": {"content": content}, "done": False}
                        for call in delta.get("tool_calls", []):
                            # Streaming tool-call deltas are not assembled here; runtimes use non-streaming tool calls.
                            yield {"tool_call_delta": call, "done": False}

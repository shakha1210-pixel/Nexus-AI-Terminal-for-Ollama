from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator

import httpx

from app.services.agent_access_service import AgentAccessError, agent_access_service
from app.providers.base import ProviderCapabilities
from app.providers.manager import ProviderCapabilityError, provider_manager


class ChatError(ValueError):
    pass


class ChatService:
    def __init__(self, store_path: Path | None = None) -> None:
        self.store_path = store_path or (Path(__file__).resolve().parents[2] / ".nexus" / "conversations")
        self._lock = threading.RLock()

    @staticmethod
    def _valid_id(value: str) -> str:
        if not re.fullmatch(r"[a-f0-9]{32}", value):
            raise ChatError("Conversation ID noto‘g‘ri.")
        return value

    def _path(self, conversation_id: str) -> Path:
        return self.store_path / f"{self._valid_id(conversation_id)}.json"

    def _read(self, conversation_id: str) -> dict:
        try:
            data = json.loads(self._path(conversation_id).read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ChatError("Suhbat topilmadi.") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ChatError("Suhbat tarixini o‘qib bo‘lmadi.") from exc
        if not isinstance(data, dict) or not isinstance(data.get("messages"), list):
            raise ChatError("Suhbat ma’lumoti noto‘g‘ri.")
        return data

    def _write(self, data: dict) -> None:
        self.store_path.mkdir(parents=True, exist_ok=True)
        target = self._path(data["id"])
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(target)

    def list_conversations(self) -> list[dict]:
        self.store_path.mkdir(parents=True, exist_ok=True)
        result = []
        for path in self.store_path.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                messages = data.get("messages", [])
                result.append({
                    "id": data["id"], "title": data.get("title", "New conversation"),
                    "updated_at": data.get("updated_at"), "message_count": len(messages),
                })
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return sorted(result, key=lambda item: item.get("updated_at") or "", reverse=True)

    def get_conversation(self, conversation_id: str) -> dict:
        return self._read(conversation_id)

    def delete_conversation(self, conversation_id: str) -> dict:
        path = self._path(conversation_id)
        try:
            path.unlink()
        except FileNotFoundError as exc:
            raise ChatError("Suhbat topilmadi.") from exc
        return {"deleted": conversation_id}

    async def stream_chat(
        self, *, model: str, message: str, conversation_id: str | None,
        agent_id: str, paths: list[str], provider_id: str | None = None,
    ) -> AsyncIterator[str]:
        model = model.strip()
        message = message.strip()
        if not model or len(model) > 160 or not message or len(message) > 20000:
            raise ChatError("Model yoki xabar bo‘sh, yoxud ruxsat etilgan hajmdan katta.")
        selected_provider = provider_id or provider_manager.active_provider_id or "ollama"
        try:
            provider_models = await provider_manager.list_models(selected_provider)
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise ChatError(f"'{selected_provider}' provider bilan bog‘lanib bo‘lmadi.") from exc
        model_info = next((item for item in provider_models if item.id == model), None)
        if model_info is None:
            raise ChatError("Tanlangan model joriy provider’da mavjud emas.")

        if conversation_id:
            data = self._read(conversation_id)
        else:
            conversation_id = uuid.uuid4().hex
            now = datetime.now(timezone.utc).isoformat()
            data = {"id": conversation_id, "title": message[:72], "created_at": now, "updated_at": now, "messages": []}

        attachments = []
        if paths:
            try:
                context = agent_access_service.build_context(agent_id, paths)
            except AgentAccessError as exc:
                raise ChatError(str(exc)) from exc
            attachments = context["attachments"]

        user_content = message
        image_data = []
        for item in attachments:
            if item["kind"] == "text":
                user_content += f"\n\n[Workspace file: {item['path']}]\n{item['content']}\n[End file]"
            elif item["kind"] == "image":
                image_data.append(item["content_base64"])
                user_content += f"\n\n[Image attachment: {item['path']}]"
        if image_data:
            try:
                provider_manager.require_capabilities(
                    selected_provider, model_info, ProviderCapabilities(vision=True)
                )
            except ProviderCapabilityError as exc:
                raise ChatError(str(exc)) from exc
        user_message = {"role": "user", "content": user_content}
        request_message = dict(user_message)
        if image_data:
            request_message["images"] = image_data
        data["messages"].append(user_message)
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._write(data)

        yield "event: meta\ndata: " + json.dumps({"conversation_id": conversation_id}) + "\n\n"
        request_messages = [*data["messages"][:-1], request_message]
        payload = {"model": model, "messages": request_messages, "stream": True}
        assistant_text = ""
        try:
            async with httpx.AsyncClient(timeout=None, auth=ollama_service.auth) as client:
                async with client.stream("POST", f"{ollama_service.base_url}/api/chat", json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if chunk.get("error"):
                            raise ChatError(str(chunk["error"])[:500])
                        content = (chunk.get("message") or {}).get("content", "")
                        if content:
                            assistant_text += content
                            yield "event: token\ndata: " + json.dumps({"content": content}, ensure_ascii=False) + "\n\n"
                        if chunk.get("done"):
                            break
            if assistant_text:
                data["messages"].append({"role": "assistant", "content": assistant_text})
                data["updated_at"] = datetime.now(timezone.utc).isoformat()
                with self._lock:
                    self._write(data)
            yield "event: done\ndata: " + json.dumps({"conversation_id": conversation_id}) + "\n\n"
        except (httpx.HTTPError, ChatError) as exc:
            yield "event: error\ndata: " + json.dumps({"message": f"Ollama chat xatosi: {type(exc).__name__}" if isinstance(exc, httpx.HTTPError) else str(exc)}, ensure_ascii=False) + "\n\n"


chat_service = ChatService()

import json
from pathlib import Path
from threading import RLock

from app.config import settings
from app.providers.adapters import OllamaAdapter, OpenAICompatibleAdapter
from app.providers.manager import provider_manager
from app.services.app_data import get_store_path
from app.services.ollama_service import ollama_service
from app.services.secrets_service import secrets_service

_LEGACY_DIR = Path(__file__).resolve().parents[2] / ".nexus"


class ProviderRuntimeService:
    """Configures the shared adapter registry and persists the active provider choice."""

    def __init__(self, store_path: Path | None = None) -> None:
        self.store_path = store_path or get_store_path("provider_runtime.json", _LEGACY_DIR / "provider_runtime.json")
        self._lock = RLock()
        if not provider_manager.registry.has("ollama"):
            provider_manager.register(OllamaAdapter(
                base_url=lambda: ollama_service.base_url,
                auth=lambda: ollama_service.auth,
                timeout=settings.request_timeout_seconds,
                provider_id="ollama",
            ))
        api_key = settings.openai_compatible_api_key or secrets_service.get("openai-compatible-api-key")
        if settings.openai_compatible_base_url and not provider_manager.registry.has("openai-compatible"):
            provider_manager.register(OpenAICompatibleAdapter(
                base_url=settings.openai_compatible_base_url,
                api_key=api_key or None,
                timeout=settings.request_timeout_seconds,
            ))
        self._active_provider = "ollama"
        self._load()
        provider_manager.set_active_provider(self._active_provider)

    def _load(self) -> None:
        try:
            payload = json.loads(self.store_path.read_text(encoding="utf-8"))
            provider_id = payload.get("active_provider") if isinstance(payload, dict) else None
            if isinstance(provider_id, str) and provider_manager.registry.has(provider_id):
                self._active_provider = provider_id
        except (OSError, ValueError):
            pass


    def refresh_openai_adapter(self) -> dict:
        """Apply current endpoint and credential values without restarting the backend."""
        with self._lock:
            base_url = settings.openai_compatible_base_url.strip()
            api_key = settings.openai_compatible_api_key or secrets_service.get("openai-compatible-api-key")
            if base_url:
                provider_manager.registry.replace(OpenAICompatibleAdapter(
                    base_url=base_url,
                    api_key=api_key or None,
                    timeout=settings.request_timeout_seconds,
                ))
                configured = True
            else:
                provider_manager.registry.remove("openai-compatible")
                configured = False
                if self._active_provider == "openai-compatible":
                    self._active_provider = "ollama"
                    provider_manager.set_active_provider("ollama")
                    self.store_path.parent.mkdir(parents=True, exist_ok=True)
                    temporary = self.store_path.with_suffix(".tmp")
                    temporary.write_text(json.dumps({"active_provider": "ollama"}, indent=2), encoding="utf-8")
                    temporary.replace(self.store_path)
            return {"provider_id": "openai-compatible", "configured": configured, "reloaded": True}

    def active(self) -> dict:
        with self._lock:
            return {"provider_id": self._active_provider}

    def set_active(self, provider_id: str) -> dict:
        if not provider_manager.registry.has(provider_id):
            raise ValueError("Provider is not configured on this backend.")
        with self._lock:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.store_path.with_suffix(".tmp")
            temporary.write_text(json.dumps({"active_provider": provider_id}, indent=2), encoding="utf-8")
            temporary.replace(self.store_path)
            self._active_provider = provider_id
            provider_manager.set_active_provider(provider_id)
        return self.active()

    async def catalog(self) -> dict:
        providers = []
        for provider_id in provider_manager.registry.list_ids():
            adapter = provider_manager.registry.get(provider_id)
            connected = await adapter.health_check()
            models = await adapter.list_models() if connected else []
            providers.append({
                "id": provider_id,
                "name": "Ollama (Local / Kaggle)" if provider_id == "ollama" else "OpenAI-compatible API",
                "configured": True,
                "connected": connected,
                "models": [{
                    "name": model.id,
                    "display_name": model.display_name or model.id,
                    "capabilities": {
                        "streaming": model.capabilities.streaming,
                        "tool_calling": model.capabilities.tool_calling,
                        "vision": model.capabilities.vision,
                        "embeddings": model.capabilities.embeddings,
                        "json_mode": model.capabilities.json_mode,
                    },
                    "metadata": model.metadata,
                } for model in models],
            })
        return {"active_provider": self.active()["provider_id"], "providers": providers}

    async def models(self, provider_id: str | None = None):
        selected = provider_id or self.active()["provider_id"]
        return await provider_manager.list_models(selected)


provider_runtime_service = ProviderRuntimeService()

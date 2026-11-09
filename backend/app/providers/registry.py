from app.providers.base import BaseAdapter


class ProviderRegistry:
    """Explicit adapter registry; provider identifiers are stable and unique."""

    def __init__(self) -> None:
        self._adapters: dict[str, BaseAdapter] = {}

    def register(self, adapter: BaseAdapter) -> None:
        provider_id = getattr(adapter, "provider_id", "")
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise ValueError("Adapter provider_id must be a non-empty string.")
        if provider_id in self._adapters:
            raise ValueError(f"Provider already registered: {provider_id}")
        self._adapters[provider_id] = adapter

    def get(self, provider_id: str) -> BaseAdapter:
        try:
            return self._adapters[provider_id]
        except KeyError as exc:
            raise KeyError(f"Unknown provider: {provider_id}") from exc

    def list_ids(self) -> list[str]:
        return list(self._adapters)

    def has(self, provider_id: str) -> bool:
        return provider_id in self._adapters

from typing import Any

from app.providers.base import BaseAdapter, ProviderModel
from app.providers.policy import FailureKind, ProviderSwitchPolicy, ProviderSwitchingEngine, SwitchDecision
from app.providers.registry import ProviderRegistry


class ProviderManager:
    """Shared provider registry and policy gate for chat and agent runtimes."""

    def __init__(self, registry: ProviderRegistry | None = None, policy: ProviderSwitchPolicy | None = None) -> None:
        self.registry = registry or ProviderRegistry()
        self.switching = ProviderSwitchingEngine(policy or ProviderSwitchPolicy())
        self.active_provider_id: str | None = None

    def register(self, adapter: BaseAdapter) -> None:
        self.registry.register(adapter)

    def set_active_provider(self, provider_id: str) -> None:
        self.registry.get(provider_id)
        self.active_provider_id = provider_id

    async def list_models(self, provider_id: str) -> list[ProviderModel]:
        return await self.registry.get(provider_id).list_models()

    async def health(self, provider_id: str) -> bool:
        return await self.registry.get(provider_id).health_check()

    def evaluate_fallback(
        self,
        *,
        source_provider: str,
        failure: FailureKind,
        switches_used: int = 0,
        attempts: int = 1,
        stream_started: bool = False,
        isolated: bool = False,
        approval_pending: bool = False,
    ) -> SwitchDecision:
        return self.switching.evaluate(
            source_provider=source_provider, failure=failure,
            switches_used=switches_used, attempts=attempts,
            stream_started=stream_started, isolated=isolated,
            approval_pending=approval_pending,
        )

    async def chat(self, provider_id: str, messages: list[dict[str, Any]], model: str, **kwargs: Any) -> dict[str, Any]:
        return await self.registry.get(provider_id).chat(messages, model, **kwargs)

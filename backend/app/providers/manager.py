from typing import Any

from app.providers.base import BaseAdapter, ProviderCapabilities, ProviderModel
from app.providers.policy import FailureKind, ProviderSwitchPolicy, ProviderSwitchingEngine, SwitchDecision
from app.providers.registry import ProviderRegistry


class ProviderCapabilityError(ValueError):
    pass


class ProviderManager:
    """Shared provider registry and policy gate for chat and agent runtimes."""

    def __init__(self, registry: ProviderRegistry | None = None, policy: ProviderSwitchPolicy | None = None) -> None:
        self.registry = registry or ProviderRegistry()
        self.switching = ProviderSwitchingEngine(policy or ProviderSwitchPolicy())
        self.active_provider_id: str | None = None

    def set_policy(self, policy: ProviderSwitchPolicy) -> None:
        self.switching = ProviderSwitchingEngine(policy)

    def register(self, adapter: BaseAdapter) -> None:
        self.registry.register(adapter)

    def set_active_provider(self, provider_id: str) -> None:
        self.registry.get(provider_id)
        self.active_provider_id = provider_id

    async def list_models(self, provider_id: str) -> list[ProviderModel]:
        return await self.registry.get(provider_id).list_models()

    async def health(self, provider_id: str) -> bool:
        return await self.registry.get(provider_id).health_check()

    def require_capabilities(
        self, provider_id: str, model: ProviderModel, required: ProviderCapabilities
    ) -> None:
        adapter = self.registry.get(provider_id)
        actual = model.capabilities
        missing = [name for name in ProviderCapabilities.__dataclass_fields__
                   if getattr(required, name) and not getattr(actual, name)]
        if missing:
            raise ProviderCapabilityError(
                f"Provider '{adapter.provider_id}' model '{model.id}' lacks required capabilities: "
                + ", ".join(missing)
            )

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
        decision = self.switching.evaluate(
            source_provider=source_provider, failure=failure,
            switches_used=switches_used, attempts=attempts,
            stream_started=stream_started, isolated=isolated,
            approval_pending=approval_pending,
        )
        if decision.allowed and decision.target_provider and not self.registry.has(decision.target_provider):
            return SwitchDecision(False, reason="The configured fallback provider is not registered or available.")
        return decision

    def confirm_fallback(
        self, decision: SwitchDecision, *, isolated: bool = False,
        approval_pending: bool = False, stream_started: bool = False,
    ) -> SwitchDecision:
        confirmed = self.switching.confirm(
            decision, isolated=isolated, approval_pending=approval_pending,
            stream_started=stream_started,
        )
        if confirmed.allowed and confirmed.target_provider and not self.registry.has(confirmed.target_provider):
            return SwitchDecision(False, reason="The confirmed fallback provider is no longer registered.")
        return confirmed

    async def chat(self, provider_id: str, messages: list[dict[str, Any]], model: str, **kwargs: Any) -> dict[str, Any]:
        return await self.registry.get(provider_id).chat(messages, model, **kwargs)


provider_manager = ProviderManager()

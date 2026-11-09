from typing import Any, AsyncIterator

from app.providers.base import BaseAdapter, ProviderCapabilities, ProviderModel
from app.providers.policy import FailureKind, ProviderSwitchPolicy, ProviderSwitchingEngine, SwitchDecision
from app.providers.registry import ProviderRegistry
from app.services.provider_resilience_service import provider_resilience_service


class ProviderCapabilityError(ValueError):
    pass


class ProviderManager:
    """Shared provider registry, resilience gate, and fallback policy for runtimes."""

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
        self, *, source_provider: str, failure: FailureKind, switches_used: int = 0,
        attempts: int = 1, stream_started: bool = False, isolated: bool = False,
        approval_pending: bool = False,
    ) -> SwitchDecision:
        decision = self.switching.evaluate(
            source_provider=source_provider, failure=failure, switches_used=switches_used,
            attempts=attempts, stream_started=stream_started, isolated=isolated,
            approval_pending=approval_pending,
        )
        if decision.allowed and decision.target_provider and not self.registry.has(decision.target_provider):
            return SwitchDecision(False, reason="The configured fallback provider is not registered or available.")
        return decision

    def confirm_fallback(
        self, decision: SwitchDecision, *, isolated: bool = False,
        approval_pending: bool = False, stream_started: bool = False,
    ) -> SwitchDecision:
        if decision.allowed and decision.target_provider and not self.registry.has(decision.target_provider):
            return SwitchDecision(False, reason="The confirmed fallback provider is no longer registered.")
        return self.switching.confirm(
            decision, isolated=isolated, approval_pending=approval_pending,
            stream_started=stream_started,
        )

    async def chat(self, provider_id: str, messages: list[dict[str, Any]], model: str, **kwargs: Any) -> dict[str, Any]:
        provider_resilience_service.before_request(provider_id)
        completed = False
        try:
            result = await self.registry.get(provider_id).chat(messages, model, **kwargs)
            completed = True
            provider_resilience_service.record_success(provider_id)
            return result
        except Exception as exc:
            provider_resilience_service.record_failure(provider_id, exc)
            raise
        finally:
            if not completed:
                provider_resilience_service.release_probe(provider_id)

    def stream(self, provider_id: str, messages: list[dict[str, Any]], model: str, **kwargs: Any) -> AsyncIterator[dict[str, Any]]:
        async def guarded_stream() -> AsyncIterator[dict[str, Any]]:
            provider_resilience_service.before_request(provider_id)
            completed = False
            try:
                async for chunk in self.registry.get(provider_id).stream(messages, model, **kwargs):
                    yield chunk
                    if chunk.get("done"):
                        provider_resilience_service.record_success(provider_id)
                # A clean stream end without an explicit done marker is still a successful transport.
                completed = True
                provider_resilience_service.record_success(provider_id)
            except Exception as exc:
                provider_resilience_service.record_failure(provider_id, exc)
                raise
            finally:
                if not completed:
                    provider_resilience_service.release_probe(provider_id)
        return guarded_stream()


provider_manager = ProviderManager()

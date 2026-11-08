"""Provider abstraction and guarded switching policy for NEXUS."""

from app.providers.base import BaseAdapter, ProviderCapabilities, ProviderModel
from app.providers.manager import ProviderCapabilityError, ProviderManager
from app.providers.policy import (
    FailureKind, ProviderSwitchPolicy, ProviderSwitchingEngine,
    SwitchDecision, SwitchingMode,
)
from app.providers.registry import ProviderRegistry
from app.providers.adapters import OllamaAdapter, OpenAICompatibleAdapter

__all__ = [
    "BaseAdapter", "ProviderCapabilities", "ProviderModel", "ProviderManager",
    "ProviderCapabilityError", "FailureKind", "ProviderSwitchPolicy",
    "ProviderSwitchingEngine", "SwitchDecision", "SwitchingMode",
    "ProviderRegistry", "OllamaAdapter", "OpenAICompatibleAdapter",
]

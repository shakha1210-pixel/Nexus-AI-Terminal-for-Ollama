"""Provider abstraction and guarded switching policy for NEXUS."""

from app.providers.base import BaseAdapter, ProviderCapabilities, ProviderModel
from app.providers.manager import ProviderManager
from app.providers.policy import (
    FailureKind,
    ProviderSwitchPolicy,
    ProviderSwitchingEngine,
    SwitchDecision,
    SwitchingMode,
)
from app.providers.registry import ProviderRegistry

__all__ = [
    "BaseAdapter", "ProviderCapabilities", "ProviderModel", "ProviderManager",
    "FailureKind", "ProviderSwitchPolicy", "ProviderSwitchingEngine",
    "SwitchDecision", "SwitchingMode", "ProviderRegistry",
]

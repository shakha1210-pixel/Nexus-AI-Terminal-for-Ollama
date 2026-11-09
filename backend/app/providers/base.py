from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator


@dataclass(frozen=True)
class ProviderCapabilities:
    streaming: bool = False
    tool_calling: bool = False
    vision: bool = False
    embeddings: bool = False
    json_mode: bool = False


@dataclass(frozen=True)
class ProviderModel:
    id: str
    display_name: str | None = None
    capabilities: ProviderCapabilities = field(default_factory=ProviderCapabilities)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseAdapter(ABC):
    """Provider adapter contract. Secrets must remain inside backend adapters."""

    provider_id: str

    @abstractmethod
    async def health_check(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def list_models(self) -> list[ProviderModel]:
        raise NotImplementedError

    @abstractmethod
    async def chat(self, messages: list[dict[str, Any]], model: str, **kwargs: Any) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def stream(
        self, messages: list[dict[str, Any]], model: str, **kwargs: Any
    ) -> AsyncIterator[dict[str, Any]]:
        raise NotImplementedError

    async def close(self) -> None:
        """Release adapter resources when applicable."""
        return None
